<?php

$host = '127.0.0.1';
$user = 'root';
$password = 'root';
$database = '';
$port = 8889; 



// --- Connect to MySQL ---
$mysqli = new mysqli($host, $user, $password, $database, $port);
if ($mysqli->connect_errno) {
    // Use a simple error message for production, log detailed errors separately
    die("Database connection failed. Please try again later.");
    // For debugging: die("Failed to connect to MySQL: (" . $mysqli->connect_errno . ") " . $mysqli->connect_error);
}
// Set charset AFTER connection for security and compatibility
$mysqli->set_charset('utf8mb4');


// --- Helper Functions ---

/**
 * Escapes HTML special characters for safe output.
 * @param string|null $str The string to escape.
 * @return string The escaped string.
 */
function e(?string $str): string {
    return htmlspecialchars((string)$str, ENT_QUOTES, 'UTF-8');
}

/**
 * Highlights search terms within a text snippet.
 * @param string $text The text snippet.
 * @param array $terms The search terms to highlight.
 * @return string The text with terms highlighted.
 */
function highlight_terms(string $text, array $terms): string {
    if (empty($terms)) {
        return $text;
    }
    // Create a pattern that matches any of the terms, case-insensitively
    $patternParts = [];
    foreach ($terms as $term) {
        $trimmedTerm = trim($term);
        if (strlen($trimmedTerm) > 0) {
            // Escape characters special to regex
            $patternParts[] = preg_quote($trimmedTerm, '/');
        }
    }
    if (empty($patternParts)) {
        return $text;
    }
    $pattern = '/(' . implode('|', $patternParts) . ')/i';
    // Use preg_replace_callback for safer replacement with HTML
    return preg_replace_callback($pattern, function($matches) {
        // Wrap the found match (case-insensitively matched) in <strong> tags
        // Use the actual matched text ($matches[0]) to preserve original casing
        return '<strong>' . $matches[0] . '</strong>';
    }, $text);
}


// --- Configuration ---
$results_per_page = 25;
$ft_min_word_len = 3; // MySQL FULLTEXT index min word length (adjust if your MySQL config differs)


// --- Input Processing ---
$query = isset($_GET['q']) ? trim($_GET['q']) : '';
$page = isset($_GET['page']) ? max(1, (int)$_GET['page']) : 1;

$original_terms = preg_split('/\s+/', $query, -1, PREG_SPLIT_NO_EMPTY);
$boolean_query_parts = [];
$final_search_query = ''; // This will hold the query string passed to SQL
$query_mode_sql = "";     // This will hold 'IN BOOLEAN MODE', 'IN NATURAL LANGUAGE MODE', or be empty
$query_explanation = "Natural Language Search"; // User-friendly explanation
$use_boolean_mode = false;
$has_short_terms = false;
$use_like_fallback = false;

// Only proceed with query building if there's an actual query
if (!empty($original_terms)) {
    // Check for short terms and build boolean parts
    foreach ($original_terms as $term) {
        if (mb_strlen($term) < $ft_min_word_len) {
            $has_short_terms = true;
        } else {
            // Basic sanitization for boolean mode operators
            $term_sanitized = preg_replace('/[+\-><()~*\"@]+/', '', $term);
            // Only add non-empty terms after sanitization
            if (!empty($term_sanitized)) {
                // Prepending '+' makes the term mandatory in boolean mode
                $boolean_query_parts[] = '+' . $term_sanitized;
            }
        }
    }

    // Decide the search strategy
    if (!empty($boolean_query_parts)) {
        // If we have valid terms >= min length, use Boolean Mode
        $final_search_query = implode(' ', $boolean_query_parts);
        $query_mode_sql = "IN BOOLEAN MODE";
        $use_boolean_mode = true;
        $query_explanation = "Boolean Mode (all terms required)";
        if ($has_short_terms) {
             $query_explanation .= " - Note: terms shorter than {$ft_min_word_len} characters were ignored.";
        }
    } elseif ($has_short_terms) {
        // If ONLY short terms exist, fall back to LIKE
        $final_search_query = '%' . $query . '%'; // Prepare for LIKE
        $query_mode_sql = ""; // No specific mode for LIKE
        $use_like_fallback = true;
        $query_explanation = "LIKE Fallback (due to short terms)";
    } else {
        // If the query had terms, but they were all sanitized away (e.g., query was just "+++")
        // Or if something unexpected happened, fall back to Natural Language with original query.
        // This case is less likely with the current logic but acts as a safety net.
        $final_search_query = $query;
        $query_mode_sql = "IN NATURAL LANGUAGE MODE";
        $query_explanation = "Natural Language Search";
    }
} else {
    // No terms entered, search query remains empty
    $query_explanation = "No search query entered.";
}

// --- Initialization ---
$results = [];
$total_results = 0;
$total_pages = 0; // Initialize to 0
$offset = 0;
$error_message = null; // To store any execution errors

// --- Database Interaction (Only if a valid query exists) ---
if ($query !== '' && $final_search_query !== '') {

    // --- Count Total Matches ---
    try {
        // Note: The JOIN in the count query might be slightly inefficient if pages can belong
        // to multiple documents, but it's needed if the WHERE clause depends on the documents table.
        // If the WHERE is only on 'pages.text', counting directly on 'pages' might be faster.
        // However, keeping the JOIN for consistency with the SELECT logic.
        if ($use_like_fallback) {
            $count_sql = "SELECT COUNT(*)
                          FROM pages p
                          JOIN documents d ON p.document_id = d.id -- Assuming join is on d.id (PK) = p.document_id (FK)
                          WHERE p.text LIKE ?";
            $count_stmt = $mysqli->prepare($count_sql);
            if (!$count_stmt) throw new Exception("Count statement preparation failed (LIKE): " . $mysqli->error);
            $count_stmt->bind_param('s', $final_search_query);
        } else {
            // Use the determined mode (Boolean or Natural Language)
            $count_sql = "SELECT COUNT(*)
                          FROM pages p
                          JOIN documents d ON p.document_id = d.id -- Assuming join is on d.id (PK) = p.document_id (FK)
                          WHERE MATCH(p.text) AGAINST(? {$query_mode_sql})";
            $count_stmt = $mysqli->prepare($count_sql);
            if (!$count_stmt) throw new Exception("Count statement preparation failed (MATCH): " . $mysqli->error);
            $count_stmt->bind_param('s', $final_search_query);
        }

        if (!$count_stmt->execute()) {
             throw new Exception("Count statement execution failed: " . $count_stmt->error);
        }
        $count_stmt->bind_result($total_results);
        $count_stmt->fetch();
        $count_stmt->close();

    } catch (Exception $e) {
        $error_message = "Error counting results: " . $e->getMessage();
        // Optionally log the full error: error_log($e->getMessage());
        $total_results = 0; // Ensure no results are shown if count fails
    }

    // --- Calculate Pagination ---
    if ($total_results > 0) {
        $total_pages = (int)ceil($total_results / $results_per_page);
        $page = max(1, min($page, $total_pages)); // Ensure page is within valid range
        $offset = ($page - 1) * $results_per_page;
    } else {
        $total_pages = 1; // Always show page 1 even if no results
        $page = 1;
        $offset = 0;
    }


    // --- Fetch Results for the Current Page ---
    if ($total_results > 0 && $error_message === null) {
        try {
            if ($use_like_fallback) {
                 $select_sql = "
                    SELECT
                        d.id AS document_sql_id,  -- The database's internal ID for the document row
                        d.document_id,            -- The ID used for filenames (e.g., hex string)
                        d.original_url,
                        p.page_number,
                        p.text,
                        1 AS relevance           -- Assign arbitrary relevance for LIKE
                    FROM pages p
                    JOIN documents d ON p.document_id = d.id -- ADJUST JOIN condition if needed
                    WHERE p.text LIKE ?
                    ORDER BY p.id ASC             -- Or some other logical order for LIKE results
                    LIMIT ? OFFSET ?
                ";
                $stmt = $mysqli->prepare($select_sql);
                if (!$stmt) throw new Exception("Select statement preparation failed (LIKE): " . $mysqli->error);
                $stmt->bind_param('sii', $final_search_query, $results_per_page, $offset);

            } else {
                 $select_sql = "
                    SELECT
                        d.id AS document_sql_id,  -- The database's internal ID for the document row
                        d.document_id,            -- The ID used for filenames (e.g., hex string)
                        d.original_url,
                        p.page_number,
                        p.text,
                        MATCH(p.text) AGAINST(? IN NATURAL LANGUAGE MODE) AS relevance
                    FROM pages p
                    JOIN documents d ON p.document_id = d.id -- ADJUST JOIN condition if needed
                    WHERE MATCH(p.text) AGAINST(? {$query_mode_sql})
                    ORDER BY relevance DESC, p.id ASC -- Order by relevance, then ID as tie-breaker
                    LIMIT ? OFFSET ?
                ";
                $stmt = $mysqli->prepare($select_sql);
                if (!$stmt) throw new Exception("Select statement preparation failed (MATCH): " . $mysqli->error);
                // Param 1: Relevance scoring (natural language query)
                // Param 2: WHERE clause filtering (boolean or natural language query)
                // Param 3: Limit
                // Param 4: Offset
                $stmt->bind_param('ssii', $query, $final_search_query, $results_per_page, $offset);
            }

            if (!$stmt->execute()) {
                 throw new Exception("Select statement execution failed: " . $stmt->error);
            }

            $res = $stmt->get_result();
            while ($row = $res->fetch_assoc()) {
                // --- Snippet Generation ---
                $text_content = $row['text'] ?? '';
                $text_content_plain = strip_tags($text_content);
                $first_pos = false;
                $snippet_context = 240;
                $context_before = 60;

                if (!empty($original_terms)) {
                    foreach ($original_terms as $term) {
                        $pos = stripos($text_content_plain, $term);
                        if ($pos !== false) {
                            if ($first_pos === false || $pos < $first_pos) {
                                $first_pos = $pos;
                            }
                        }
                    }
                }

                $start = 0;
                if ($first_pos !== false) {
                    $start = max(0, $first_pos - $context_before);
                    if ($start > 0) {
                        $space_pos = strrpos(substr($text_content_plain, 0, $start), ' ');
                        if ($space_pos !== false) {
                            $start = $space_pos + 1;
                        }
                    }
                }

                $snippet_raw = mb_substr($text_content_plain, $start, $snippet_context, 'UTF-8');
                $prefix_ellipsis = ($start > 0) ? '... ' : '';
                $suffix_ellipsis = (mb_strlen($text_content_plain, 'UTF-8') > $start + $snippet_context) ? ' ...' : '';
                $escaped_snippet = e($snippet_raw);
                $highlighted_snippet = $prefix_ellipsis . highlight_terms($escaped_snippet, $original_terms) . $suffix_ellipsis;

                // --- Store result data using the correct IDs ---
                $pdf_filename_id = (string)($row['document_id'] ?? ''); // Get the ID for the PDF filename
                // $database_doc_pk = $row['document_sql_id']; // Get the internal DB PK if needed elsewhere

                $results[] = [
                    // Store the ID used for filenames as 'document_id' in the results array
                    'document_id' => $pdf_filename_id,
                    // Use the $pdf_filename_id to build the viewer URL
                    'viewer_url' => '/pdfjs/web/viewer.html?file=' . urlencode('/jfk_documents_original/' . $pdf_filename_id . '.pdf') . '#page=' . (int)$row['page_number'],
                    'original_url' => e($row['original_url']) . '#page=' . (int)$row['page_number'],
                    'page_number' => (int)$row['page_number'],
                    'snippet' => $highlighted_snippet
                    // Optionally add 'document_sql_id' => $database_doc_pk if you need the PK later
                ];
            }
            $stmt->close();

        } catch (Exception $e) {
             $error_message = "Error fetching results: " . $e->getMessage();
             // Optionally log the full error: error_log($e->getMessage());
             $results = []; // Clear results if fetch fails
        }
    }
}

$mysqli->close();

?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <!-- Make site responsive -->
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JFK Document Search</title>
    <style>
        /* --- Basic Reset & Defaults --- */
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        html {
            font-size: 16px; /* Base font size */
             -webkit-text-size-adjust: 100%; /* Prevent font scaling override on iOS */
             scroll-behavior: smooth;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol";
            line-height: 1.6;
            color: #333;
            background-color: #f9f9f9;
            display: flex;
            flex-direction: column;
            min-height: 100vh; /* Ensure body takes full viewport height */
        }

        /* --- Layout --- */
        .wrapper {
            flex: 1; /* Allows main content to grow and push footer down */
            display: flex;
            flex-direction: column;
            width: 100%;
        }
        main {
            width: 100%;
            max-width: 800px; /* Max width for readability on larger screens */
            margin: 0 auto; /* Center content */
            padding: 1.5rem 1rem; /* Responsive padding */
            flex: 1; /* Allow main to grow */
        }
        footer {
            background: #eee;
            padding: 1.5rem 1rem;
            text-align: center;
            border-top: 1px solid #ccc;
            margin-top: 2rem; /* Space above footer */
            width: 100%;
        }

        /* --- Typography --- */
        h1, h2, h3 {
            margin-bottom: 1rem;
            line-height: 1.3;
            color: #222;
        }
        h1 { font-size: 2rem; }
        h2 { font-size: 1.6rem; }
        h3 { font-size: 1.1rem; color: #555; }
        p { margin-bottom: 1rem; }
        a {
            color: #0056b3; /* Standard blue link color */
            text-decoration: none;
        }
        a:hover, a:focus {
            text-decoration: underline;
            color: #003d80;
        }
        strong {
            background-color: #fff3cd; /* Light yellow highlight */
            padding: 0.1em 0.2em;
            border-radius: 3px;
            font-weight: bold; /* Ensure it's bold */
        }

        /* --- Form --- */
        .search-form {
            margin-bottom: 2rem;
            display: flex;
            flex-wrap: wrap; /* Allow button to wrap below input */
            gap: 0.75rem; /* Space between input and button */
        }
        .search-form input[type="text"] {
            flex-grow: 1; /* Input takes available space */
            padding: 0.75rem;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 1rem;
            min-width: 150px; /* Prevent input becoming too small */
        }
        .search-form input[type="submit"] {
            padding: 0.75rem 1.25rem;
            border: none;
            background-color: #0056b3;
            color: white;
            border-radius: 4px;
            font-size: 1rem;
            cursor: pointer;
            transition: background-color 0.2s ease;
            flex-shrink: 0; /* Prevent button from shrinking too much */
        }
        .search-form input[type="submit"]:hover,
        .search-form input[type="submit"]:focus {
            background-color: #003d80;
        }

        /* --- Results --- */
        .results-info {
            margin-bottom: 1.5rem;
            font-size: 0.95rem;
            color: #555;
        }
        .results-info strong {
             background: none; /* Don't highlight query in the info line */
             font-weight: bold;
             color: #111;
        }
        .result {
            /* Keep other properties like width and style the same */
            border-bottom: 2px solid #aaa; /* Changed #eee to #ccc */
            /* Other existing styles for .result should remain */
            margin-bottom: 1.5rem;
            padding-bottom: 1.5rem;
        }
        /* Also ensure the :last-child rule still removes the border */
        .result:last-child {
            border-bottom: none;
            /* ... other last-child styles ... */
        }
        .result-links div {
            margin-bottom: 0.5rem;
        }
        .result-links a {
            font-size: 1.1rem;
            font-weight: 500;
             word-break: break-all; /* Break long URLs if needed */
        }
         .result-links a .icon { /* Style icons */
             display: inline-block;
             width: 1em; /* Size relative to font */
             height: 1em;
             margin-right: 0.4em;
             vertical-align: -0.1em; /* Align better with text */
         }
        .snippet {
            font-size: 0.95rem;
            color: #444;
            margin-top: 0.75rem;
            overflow-wrap: break-word; /* Break long words if they overflow */
        }
        .no-results, .error-message {
            padding: 1rem;
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
            border-radius: 4px;
            margin-top: 1.5rem;
        }
         .error-message {
             background-color: #f8d7da;
             border-color: #f5c6cb;
             color: #721c24;
         }
         .query-explanation {
             font-style: italic;
             font-size: 0.9em;
             color: #666;
             margin-bottom: 1.5rem;
             margin-top: -1rem; /* Pull closer to form */
         }

        /* --- Pagination --- */
        .pagination {
            margin-top: 2.5rem;
            display: flex;
            flex-wrap: wrap; /* Allow wrapping on small screens */
            justify-content: center; /* Center links horizontally */
            gap: 0.5rem; /* Space between pagination items */
            list-style: none; /* Remove default list styles if using ul/li */
        }
        .pagination a, .pagination span {
            display: inline-block;
            padding: 0.5rem 0.9rem;
            border: 1px solid #ccc;
            border-radius: 4px;
            text-decoration: none;
            color: #0056b3;
            background-color: #fff;
            font-size: 0.9rem;
            line-height: 1.2; /* Ensure consistent height */
            min-width: 2.5em; /* Ensure minimum width for tap targets */
            text-align: center;
        }
        .pagination a:hover, .pagination a:focus {
            background-color: #eee;
            text-decoration: none;
        }
        .pagination .active {
            font-weight: bold;
            background-color: #0056b3;
            color: white;
            border-color: #0056b3;
            cursor: default;
        }
        .pagination .disabled, .pagination span { /* Style for '...' */
            color: #aaa;
            background-color: #f9f9f9;
            border-color: #eee;
            cursor: default;
        }

        /* --- Footer Specific --- */
        footer h3 {
            font-size: 1rem;
            color: #444;
            margin-bottom: 0.5rem;
        }
        footer a {
            color: #0056b3;
        }
        footer a:hover {
            color: #003d80;
        }

        /* --- Utility --- */
        .sr-only { /* Screen reader only text */
           position: absolute;
           width: 1px;
           height: 1px;
           padding: 0;
           margin: -1px;
           overflow: hidden;
           clip: rect(0, 0, 0, 0);
           white-space: nowrap;
           border-width: 0;
        }

    </style>
</head>
<body>
    <div class="wrapper">
        <main>
            <h1>JFK Document Search</h1>
            <!-- Keep secondary headings semantic but less visually prominent if desired -->
            <h2>2025 Release Documents</h2>
            <h3>Last Data Update: March 20, 2025</h3>
            <p><small>AI was used to convert PDF images into searchable text. Links go to the original document page on archives.gov or a mobile-friendly PDF viewer to the specific page. Work is being done to improve the image to text and also to open source all code used to make this. We also plan to implement an Large Language Model (LLM) using this data sometime in the near future.</small></p>

            <form method="get" action="" class="search-form" role="search">
                 <label for="search-input" class="sr-only">Search Documents</label>
                <input type="text" id="search-input" name="q" placeholder="Enter search terms..." value="<?php echo e($query); ?>" aria-label="Search Documents">
                <input type="submit" value="Search">
            </form>

            <?php // Display search results area only if a query was submitted ?>
            <?php if ($query !== ''): ?>
                 <div class="query-explanation">Search mode: <?php echo e($query_explanation); ?></div>

                <?php // Display error message if something went wrong during DB interaction ?>
                <?php if ($error_message): ?>
                    <p class="error-message">Sorry, there was an error processing your request. Please try again later.</p>
                    <?php /* Optionally display detailed error for admins/debugging: echo '<p class="error-message">'.e($error_message).'</p>'; */ ?>

                <?php // Display results count and info ?>
                <?php elseif ($total_results > 0): ?>
                    <p class="results-info">
                        Found <?php echo number_format($total_results); ?> results for "<strong><?php echo e($query); ?></strong>".
                        Showing page <?php echo $page; ?> of <?php echo $total_pages; ?>.
                    </p>

                    <?php // Loop through and display results ?>
                    <?php foreach ($results as $result): ?>
                        <div class="result">
                            <div class="result-links">
                                <div>
                                     <a href="<?php echo $result['viewer_url']; ?>" target="_blank" rel="noopener noreferrer">
                                         <span class="icon" aria-hidden="true">📄</span>Document <?php echo $result["document_id"]; ?> : Page <?php echo $result['page_number']; ?> (Mobile Viewer)
                                     </a>
                                </div>
                                <br />
                                <div>
                                     <a href="<?php echo $result['original_url']; ?>" target="_blank" rel="noopener noreferrer">
                                         <span class="icon" aria-hidden="true">🌐</span> View Original Source (archives.gov)
                                     </a>
                                </div>
                            </div>
                            <br />
                            <div class="snippet">
                                <?php echo $result['snippet']; // Snippet is already escaped and highlighted ?>
                            </div>
                            <br />
                             <!-- Debug info removed -->
                        </div>
                    <?php endforeach; ?>

                    <?php // Display Pagination if more than one page ?>
                    <?php if ($total_pages > 1): ?>
                        <nav class="pagination" aria-label="Search Results Pages">
                            <?php // Previous Page Link ?>
                            <?php if ($page > 1): ?>
                                <a href="?q=<?php echo urlencode($query); ?>&page=<?php echo $page - 1; ?>">« <span class="sr-only">Previous Page</span></a>
                            <?php else: ?>
                                <span class="disabled">« <span class="sr-only">Previous Page</span></span>
                            <?php endif; ?>

                            <?php
                            // --- Simple Pagination Logic (Improved) ---
                            $range = 2; // Number of links around the current page
                            $start = max(1, $page - $range);
                            $end = min($total_pages, $page + $range);

                            // Show '1 ...' if needed
                            if ($start > 1) {
                                echo '<a href="?q=' . urlencode($query) . '&page=1" aria-label="Page 1">1</a>';
                                if ($start > 2) {
                                    echo '<span class="disabled">...</span>';
                                }
                            }

                            // Links around the current page
                            for ($i = $start; $i <= $end; $i++) {
                                if ($i == $page) {
                                    echo '<span class="active" aria-current="page">' . $i . '</span>';
                                } else {
                                    echo '<a href="?q=' . urlencode($query) . '&page=' . $i . '" aria-label="Page ' . $i . '">' . $i . '</a>';
                                }
                            }

                            // Show '... last' if needed
                            if ($end < $total_pages) {
                                if ($end < $total_pages - 1) {
                                    echo '<span class="disabled">...</span>';
                                }
                                echo '<a href="?q=' . urlencode($query) . '&page=' . $total_pages . '" aria-label="Page ' . $total_pages . '">' . $total_pages . '</a>';
                            }
                            ?>

                            <?php // Next Page Link ?>
                            <?php if ($page < $total_pages): ?>
                                <a href="?q=<?php echo urlencode($query); ?>&page=<?php echo $page + 1; ?>"><span class="sr-only">Next Page</span> »</a>
                            <?php else: ?>
                                <span class="disabled"><span class="sr-only">Next Page</span> »</span>
                            <?php endif; ?>
                        </nav>
                    <?php endif; // end pagination check ?>

                <?php // Display 'No results' message ?>
                <?php else: ?>
                    <p class="no-results">No documents found matching "<strong><?php echo e($query); ?></strong>". Try different keywords?</p>
                <?php endif; ?>

            <?php // Initial state (no query entered) - Optionally show a prompt ?>
            <?php elseif (empty($error_message)): // Only show prompt if no error occurred and no query was run ?>
                 <p>Enter terms above to search the JFK document archive.</p>
            <?php elseif ($error_message): // Show error if it occurred before search attempt (e.g., connection) ?>
                 <p class="error-message">Sorry, there was an error connecting to the search service.</p>
            <?php endif; ?>

        </main>

        <footer>
            <h3>Part of: Mineral Social Coop</h3>
            <h3>Programmed By: Karl Appel</h3>
            <h3><a href="https://www.linkedin.com/in/karl-appel-ab9a2b65/" target="_blank" rel="noopener noreferrer">LinkedIn Profile</a></h3>
        </footer>
    </div> <!-- /.wrapper -->
</body>
</html>