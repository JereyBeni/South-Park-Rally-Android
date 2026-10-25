package com.sprally.port;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

import androidx.documentfile.provider.DocumentFile;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * Primera ejecución: importa los assets desde un .zip o desde una carpeta
 * elegida por el usuario hacia files/game_assets. Después abre GameActivity.
 */
public class ImportActivity extends Activity {
    private static final int REQ_ZIP = 1;
    private static final int REQ_TREE = 2;

    private interface Job {
        void run(File dest) throws IOException;
    }

    private TextView status;
    private Button zipBtn;
    private Button folderBtn;
    private int copied;

    public static File assetsDir(Context c) {
        return new File(c.getFilesDir(), "game_assets");
    }

    // Fuera de game_assets para que no aparezca como un archivo más del juego.
    private static File markerFile(Context c) {
        return new File(c.getFilesDir(), "game_assets.imported");
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        if (markerFile(this).exists()) {
            startGame();
            return;
        }

        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(48, 48, 48, 48);

        status = new TextView(this);
        status.setTextSize(16);
        status.setText("Importá tu copia de South Park Rally (PC): un .zip con el juego o la carpeta ya extraída.");
        layout.addView(status);

        zipBtn = new Button(this);
        zipBtn.setText("Elegir archivo .zip");
        zipBtn.setOnClickListener(v -> pickZip());
        layout.addView(zipBtn);

        folderBtn = new Button(this);
        folderBtn.setText("Elegir carpeta");
        folderBtn.setOnClickListener(v -> pickFolder());
        layout.addView(folderBtn);

        setContentView(layout);
    }

    private void pickZip() {
        Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        i.addCategory(Intent.CATEGORY_OPENABLE);
        i.setType("*/*");
        i.putExtra(Intent.EXTRA_MIME_TYPES, new String[] {
                "application/zip", "application/x-zip-compressed", "application/octet-stream"});
        startActivityForResult(i, REQ_ZIP);
    }

    private void pickFolder() {
        startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE), REQ_TREE);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (resultCode != RESULT_OK || data == null || data.getData() == null) return;
        final Uri uri = data.getData();
        if (requestCode == REQ_ZIP) {
            runImport(dest -> unzip(uri, dest));
        } else if (requestCode == REQ_TREE) {
            runImport(dest -> {
                DocumentFile root = DocumentFile.fromTreeUri(this, uri);
                if (root == null) throw new IOException("No se pudo abrir la carpeta");
                copyTree(root, dest);
            });
        }
    }

    private void runImport(Job job) {
        setBusy(true);
        new Thread(() -> {
            try {
                File dest = assetsDir(this);
                deleteRecursive(dest);  // descarta importaciones a medias
                dest.mkdirs();
                copied = 0;
                job.run(dest);
                if (copied == 0) throw new IOException("no se encontraron archivos");
                markerFile(this).createNewFile();
                runOnUiThread(this::startGame);
            } catch (IOException e) {
                runOnUiThread(() -> {
                    status.setText("Error al importar: " + e.getMessage());
                    setBusy(false);
                });
            }
        }).start();
    }

    private void unzip(Uri uri, File dest) throws IOException {
        String destPath = dest.getCanonicalPath() + File.separator;
        try (InputStream raw = getContentResolver().openInputStream(uri)) {
            if (raw == null) throw new IOException("no se pudo abrir el zip");
            ZipInputStream zin = new ZipInputStream(raw);
            byte[] buf = new byte[64 * 1024];
            ZipEntry e;
            while ((e = zin.getNextEntry()) != null) {
                File target = new File(dest, e.getName().replace('\\', '/'));
                if (!target.getCanonicalPath().startsWith(destPath)) continue;  // zip-slip
                if (e.isDirectory()) {
                    target.mkdirs();
                    continue;
                }
                File parent = target.getParentFile();
                if (parent != null) parent.mkdirs();
                try (OutputStream out = new FileOutputStream(target)) {
                    int n;
                    while ((n = zin.read(buf)) > 0) out.write(buf, 0, n);
                }
                progress();
            }
        }
    }

    private void copyTree(DocumentFile dir, File dest) throws IOException {
        for (DocumentFile child : dir.listFiles()) {
            String name = child.getName();
            if (name == null) continue;
            File target = new File(dest, name);
            if (child.isDirectory()) {
                target.mkdirs();
                copyTree(child, target);
            } else {
                try (InputStream in = getContentResolver().openInputStream(child.getUri());
                     OutputStream out = new FileOutputStream(target)) {
                    if (in == null) throw new IOException("no se pudo leer " + name);
                    byte[] buf = new byte[64 * 1024];
                    int n;
                    while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
                }
                progress();
            }
        }
    }

    private void progress() {
        copied++;
        if (copied % 20 == 0) {
            final int n = copied;
            runOnUiThread(() -> status.setText("Importando… " + n + " archivos"));
        }
    }

    private void setBusy(boolean busy) {
        zipBtn.setEnabled(!busy);
        folderBtn.setEnabled(!busy);
        if (busy) status.setText("Importando…");
    }

    private static void deleteRecursive(File f) {
        File[] children = f.listFiles();
        if (children != null) for (File c : children) deleteRecursive(c);
        f.delete();
    }

    private void startGame() {
        startActivity(new Intent(this, GameActivity.class));
        finish();
    }
}
