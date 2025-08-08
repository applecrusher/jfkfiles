package com.example.PNGToText;

import net.sourceforge.tess4j.*;
import org.json.JSONObject;
import org.json.JSONArray;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.awt.*;
import java.awt.image.RescaleOp;
import java.io.*;
import java.nio.file.*;
import java.util.List;
import java.util.*;
import java.util.concurrent.*;

public class App {
    private static final Path IMAGE_DIR = Paths.get(System.getProperty("user.dir"), "..", "..", "..", "corpus", "mlk_documents_imgs").toAbsolutePath().normalize();
    private static final Path OUTPUT_DIR = Paths.get(System.getProperty("user.dir"), "..", "..", "..", "corpus", "mlk_documents_json_v1").toAbsolutePath().normalize();
    private static final int NUM_THREADS = Math.max(Runtime.getRuntime().availableProcessors() - 2, 1);

    public static void main(String[] args) {
        System.setProperty("jna.library.path", "/opt/homebrew/lib");

        try {
            Files.createDirectories(OUTPUT_DIR);
            runOCR();
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public static void runOCR() throws IOException {
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
                    JSONObject data = processImage(imageFile, pageIndex);
                    if (data != null) {
                        Path outputPath = OUTPUT_DIR.resolve(imageFile.getName().replaceAll("\\.[^.]+$", ".json"));
                        try (BufferedWriter writer = Files.newBufferedWriter(outputPath)) {
                            writer.write(data.toString(2));
                        }
                    }
                } catch (IOException e) {
                    System.err.println("IO error processing " + imageFile.getName() + ": " + e.getMessage());
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
        }
    }

    public static JSONObject processImage(File imageFile, int pageNumber) {
        try {
            BufferedImage img = preprocessImageSafely(ImageIO.read(imageFile));

            ITesseract tesseract = new Tesseract();
            tesseract.setDatapath("/opt/homebrew/share/tessdata");
            tesseract.setTessVariable("user_defined_dpi", "300");
            tesseract.setLanguage("eng");
            tesseract.setOcrEngineMode(ITessAPI.TessOcrEngineMode.OEM_LSTM_ONLY);
            tesseract.setPageSegMode(ITessAPI.TessPageSegMode.PSM_AUTO);

            String text = tesseract.doOCR(img);
            List<Word> words = tesseract.getWords(img, ITessAPI.TessPageSegMode.PSM_AUTO);

            JSONArray textArray = new JSONArray();
            List<Double> confidences = new ArrayList<>();
            for (Word word : words) {
                if (word.getConfidence() > 60) {
                    textArray.put(word.getText());
                    confidences.add(word.getConfidence() / 100.0);
                }
            }

            double avgConfidence = confidences.isEmpty() ? 0.0 : confidences.stream().mapToDouble(Double::doubleValue).average().orElse(0.0);

            JSONObject metadata = new JSONObject();
            metadata.put("page_number", pageNumber);
            metadata.put("dimensions", new JSONArray(Arrays.asList(img.getWidth(), img.getHeight())));
            metadata.put("confidence", Math.round(avgConfidence * 10000.0) / 10000.0);
            metadata.put("ocr_engine", "Tesseract (Tess4J)");
            metadata.put("text_blocks", textArray.length());

            JSONObject result = new JSONObject();
            result.put("filename", imageFile.getName());
            result.put("text", text.trim());
            result.put("metadata", metadata);

            return result;

        } catch (Exception e) {
            System.err.println("Error processing " + imageFile.getName() + ": " + e.getMessage());
            return null;
        }
    }

public static BufferedImage preprocessImageSafely(BufferedImage original) {
    if (original == null) {
        System.err.println("Error: Original image is null.");
        return null;
    }

    int width = original.getWidth();
    int height = original.getHeight();

    if (width < 3 || height < 10) {
        System.err.printf("Warning: Tiny image detected (%dx%d). Upscaling for OCR...\n", width, height);

        // Upscale to minimum OCR-safe size (e.g., 300x300)
        int targetWidth = Math.max(300, width * 5);
        int targetHeight = Math.max(300, height * 5);

        Image scaled = original.getScaledInstance(targetWidth, targetHeight, Image.SCALE_SMOOTH);
        BufferedImage resized = new BufferedImage(targetWidth, targetHeight, BufferedImage.TYPE_INT_RGB);
        Graphics2D g2d = resized.createGraphics();
        g2d.drawImage(scaled, 0, 0, null);
        g2d.dispose();

        return toGrayscale(resized);
    }

    return toGrayscale(original);
}

private static BufferedImage toGrayscale(BufferedImage img) {
    BufferedImage gray = new BufferedImage(img.getWidth(), img.getHeight(), BufferedImage.TYPE_BYTE_GRAY);
    Graphics g = gray.getGraphics();
    g.drawImage(img, 0, 0, null);
    g.dispose();
    return gray;
}

}


