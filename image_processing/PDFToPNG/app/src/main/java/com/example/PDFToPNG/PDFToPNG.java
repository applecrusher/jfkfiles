package com.example.PDFToPNG;

import java.awt.image.BufferedImage;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.Arrays;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import javax.imageio.ImageIO;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.rendering.ImageType;
import org.apache.pdfbox.rendering.PDFRenderer;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.concurrent.atomic.AtomicInteger;


public class PDFToPNG {

    private static final int NUM_THREADS = 4;
    
    private static final Path ERROR_LOG = Paths.get(System.getProperty("user.dir"), "..", "..", ".." , "error_logs", "pdf_to_png_errors.log").normalize();
    private static final AtomicInteger pagesProcessed = new AtomicInteger(0);

    public static void main(String[] args) {
        Path pdfDirPath = Paths.get(System.getProperty("user.dir"), "..", "..", ".." , "corpus", "jfk_documents").normalize();
        Path outputDirPath = Paths.get(System.getProperty("user.dir"), "..", "..", "..", "corpus", "jfk_documents_imgs").normalize();
        
        System.out.println(pdfDirPath.toString());

        File outputDir = new File(outputDirPath.toString());
        if (!outputDir.exists()) {
            outputDir.mkdirs();
        }

        ExecutorService executor = Executors.newFixedThreadPool(NUM_THREADS);

        File pdfDir = new File(pdfDirPath.toString());
        File[] pdfFiles = pdfDir.listFiles((dir, name) -> name.toLowerCase().endsWith(".pdf"));

        if (pdfFiles != null) {
            Arrays.sort(pdfFiles, (f1, f2) -> Long.compare(f2.length(), f1.length()));
            for (File pdfFile : pdfFiles) {
                if (pdfFile.getName().startsWith(".")) continue;
                executor.submit(() -> convertPdfToImages(pdfFile, outputDirPath.toString()));
            }
        } else {
            System.out.println("No PDF files found in the specified directory.");
        }

        executor.shutdown();
        try {
            if (!executor.awaitTermination(24, TimeUnit.HOURS)) {
                executor.shutdownNow();
            }
        } catch (InterruptedException e) {
            executor.shutdownNow();
            Thread.currentThread().interrupt();
        }
    }

    private static void convertPdfToImages(File pdfFile, String outputDirPath) {
        try (PDDocument document = PDDocument.load(pdfFile)) {
            PDFRenderer pdfRenderer = new PDFRenderer(document);
            String baseName = pdfFile.getName().substring(0, pdfFile.getName().lastIndexOf('.'));

            for (int page = 0; page < document.getNumberOfPages(); ++page) {
                BufferedImage bim = pdfRenderer.renderImageWithDPI(page, 300, ImageType.RGB);
                String fileName = String.format("%s_page_%04d.png", baseName, page + 1);
                File outputFile = new File(outputDirPath, fileName);
                ImageIO.write(bim, "png", outputFile);

                int totalPages = pagesProcessed.incrementAndGet();
                if (totalPages % 20 == 0) {
                    System.out.println("Pages Processed: " + totalPages);
                }
            }
        } catch (IOException e) {
            logError("Exception while converting PDF: " + pdfFile.getName(), e);
        }
    }

    private static void logError(String message, Exception e) {
        try (FileWriter fw = new FileWriter(ERROR_LOG.toString(), true);
             PrintWriter pw = new PrintWriter(fw)) {
            pw.println("[ERROR] " + message);
            e.printStackTrace(pw);
        } catch (IOException ioException) {
            System.err.println("Failed to log error: " + ioException.getMessage());
            ioException.printStackTrace();
        }
    }
}