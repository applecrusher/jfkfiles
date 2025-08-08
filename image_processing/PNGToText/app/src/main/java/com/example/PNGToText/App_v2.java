package com.example.PNGToText;

import net.sourceforge.tess4j.*;
import org.json.JSONObject;
import org.json.JSONArray;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.awt.image.ConvolveOp;
import java.awt.image.Kernel;
import java.awt.image.RescaleOp;
import java.awt.*;
import java.awt.image.BufferedImageOp;
import java.io.*;
import java.nio.file.*;
import java.util.List;
import java.util.*;
import java.util.concurrent.*;

public class App_v2 {
    private static final Path IMAGE_DIR = Paths.get(System.getProperty("user.dir"), "..", "..", "..", "corpus", "mlk_documents_imgs").toAbsolutePath().normalize();
    private static final Path OUTPUT_DIR = Paths.get(System.getProperty("user.dir"), "..", "..", "..", "corpus", "mlk_documents_json_v2").toAbsolutePath().normalize();
    private static final Path ERROR_LOG = Paths.get(System.getProperty("user.dir"), "..", "..", "..", "error_logs", "png_to_text.log").toAbsolutePath().normalize();
    private static final int NUM_THREADS = Runtime.getRuntime().availableProcessors();

    public static void main(String[] args) {
        System.setProperty("jna.library.path", "/opt/homebrew/lib");
        System.out.println("APP V2 Launching");
        try {
            Files.createDirectories(OUTPUT_DIR);
            Files.createDirectories(ERROR_LOG.getParent());

            BufferedWriter errorWriter = Files.newBufferedWriter(ERROR_LOG, StandardOpenOption.CREATE, StandardOpenOption.APPEND);
            runOCR(errorWriter);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public static void runOCR(BufferedWriter errorWriter) throws IOException {
        File[] imageFiles = IMAGE_DIR.toFile().listFiles((dir, name) -> {
            String lower = name.toLowerCase();
            return lower.endsWith(".png") || lower.endsWith(".jpg") || lower.endsWith(".jpeg");
        });

        if (imageFiles == null || imageFiles.length == 0) return;
        Arrays.sort(imageFiles);

        ExecutorService executor = Executors.newFixedThreadPool(NUM_THREADS);
        CountDownLatch latch = new CountDownLatch(imageFiles.length);

        for (int i = 0; i < imageFiles.length; i++) {
            final int pageIndex = i + 1;
            final File imageFile = imageFiles[i];

            executor.submit(() -> {
                try {
                    System.out.printf("Processing %d/%d: %s%n", pageIndex, imageFiles.length, imageFile.getName());
                    JSONObject data = processImage(imageFile, pageIndex, errorWriter);
                    if (data != null) {
                        Path outputPath = OUTPUT_DIR.resolve(imageFile.getName().replaceAll("\\.[^.]+$", ".json"));
                        try (BufferedWriter writer = Files.newBufferedWriter(outputPath)) {
                            writer.write(data.toString(2));
                        }
                    }
                } catch (IOException e) {
                    logError(errorWriter, "IO error processing " + imageFile.getName() + ": " + e.getMessage());
                } finally {
                    latch.countDown();
                }
            });
        }

        try {
            latch.await();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } finally {
            executor.shutdown();
            errorWriter.close();
        }
    }

    public static JSONObject processImage(File imageFile, int pageNumber, BufferedWriter errorWriter) {
        try {
            BufferedImage rawImg = ImageIO.read(imageFile);
            if (rawImg == null) {
                logError(errorWriter, "Unreadable image: " + imageFile.getName());
                return null;
            }

            BufferedImage safeImg = ensureMinimumDimensions(rawImg, 32, 32);
            BufferedImage preprocessed = preprocessImageSafely(safeImg);

            ITesseract tesseract = new Tesseract();
            tesseract.setDatapath("/opt/homebrew/share/tessdata");
            tesseract.setLanguage("eng");
            tesseract.setTessVariable("user_defined_dpi", "300");
            tesseract.setPageSegMode(ITessAPI.TessPageSegMode.PSM_AUTO);
            tesseract.setOcrEngineMode(ITessAPI.TessOcrEngineMode.OEM_LSTM_ONLY);

            String text = tesseract.doOCR(preprocessed);
            JSONArray textArray = new JSONArray();
            List<Double> confidences = new ArrayList<>();

            try {
                List<Word> words = tesseract.getWords(preprocessed, ITessAPI.TessPageSegMode.PSM_AUTO);
                for (Word word : words) {
                    if (word.getConfidence() > 60) {
                        textArray.put(word.getText());
                        confidences.add(word.getConfidence() / 100.0);
                    }
                }
            } catch (Exception wordError) {
                logError(errorWriter, "Word-level error in " + imageFile.getName() + ": " + wordError.getMessage());
            }

            double avgConfidence = confidences.isEmpty() ? 0.0 : confidences.stream().mapToDouble(Double::doubleValue).average().orElse(0.0);

            JSONObject metadata = new JSONObject();
            metadata.put("page_number", pageNumber);
            metadata.put("dimensions", new JSONArray(Arrays.asList(preprocessed.getWidth(), preprocessed.getHeight())));
            metadata.put("confidence", Math.round(avgConfidence * 10000.0) / 10000.0);
            metadata.put("ocr_engine", "Tesseract (Tess4J)");
            metadata.put("text_blocks", textArray.length());

            JSONObject result = new JSONObject();
            result.put("filename", imageFile.getName());
            result.put("text", text.trim());
            result.put("metadata", metadata);

            return result;

        } catch (Exception e) {
            logError(errorWriter, "Error processing " + imageFile.getName() + ": " + e.getMessage());
            return null;
        }
    }

    public static BufferedImage preprocessImageSafely(BufferedImage original) {
        BufferedImage gray = new BufferedImage(original.getWidth(), original.getHeight(), BufferedImage.TYPE_BYTE_GRAY);
        Graphics g = gray.getGraphics();
        g.drawImage(original, 0, 0, null);
        g.dispose();

        BufferedImage enhanced = enhanceContrast(gray);
        BufferedImage denoised = denoiseImage(enhanced);
        BufferedImage finalImg = adaptiveThreshold(denoised);

        return finalImg;
    }

    public static BufferedImage enhanceContrast(BufferedImage img) {
        BufferedImage contrasted = new BufferedImage(img.getWidth(), img.getHeight(), img.getType());
        RescaleOp rescale = new RescaleOp(1.5f, 0, null);
        rescale.filter(img, contrasted);
        return contrasted;
    }

    public static BufferedImage denoiseImage(BufferedImage img) {
        float[] kernel = {
            1f/9f, 1f/9f, 1f/9f,
            1f/9f, 1f/9f, 1f/9f,
            1f/9f, 1f/9f, 1f/9f
        };
        BufferedImageOp op = new ConvolveOp(new Kernel(3, 3, kernel));
        return op.filter(img, null);
    }

    public static BufferedImage adaptiveThreshold(BufferedImage gray) {
        int width = gray.getWidth();
        int height = gray.getHeight();
        BufferedImage binary = new BufferedImage(width, height, BufferedImage.TYPE_BYTE_BINARY);
        Graphics2D g2d = binary.createGraphics();
        g2d.drawImage(gray, 0, 0, null);
        g2d.dispose();
        return binary;
    }

    public static BufferedImage ensureMinimumDimensions(BufferedImage img, int minWidth, int minHeight) {
        int width = img.getWidth();
        int height = img.getHeight();

        if (width >= minWidth && height >= minHeight) return img;

        BufferedImage padded = new BufferedImage(
                Math.max(width, minWidth),
                Math.max(height, minHeight),
                img.getType()
        );

        Graphics2D g = padded.createGraphics();
        g.setColor(Color.WHITE);
        g.fillRect(0, 0, padded.getWidth(), padded.getHeight());
        g.drawImage(img, 0, 0, null);
        g.dispose();
        return padded;
    }

    public static void logError(BufferedWriter errorWriter, String message) {
        synchronized (errorWriter) {
            try {
                errorWriter.write(String.format("[%s] %s%n", new Date(), message));
                errorWriter.flush();
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
    }
}
