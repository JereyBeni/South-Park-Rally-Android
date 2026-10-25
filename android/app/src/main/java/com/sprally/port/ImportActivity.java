package com.sprally.port;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.widget.TextView;

import androidx.documentfile.provider.DocumentFile;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

/**
 * Pide la carpeta del juego (PC) con el selector del sistema y la copia a
 * files/game_assets. Cuando termina, abre GameActivity (SDL).
 */
public class ImportActivity extends Activity {
    private static final int REQ_TREE = 1;
    private static final String MARKER = ".imported";

    private TextView status;
    private int copied;

    public static File assetsDir(Context c) {
        return new File(c.getFilesDir(), "game_assets");
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        status = new TextView(this);
        status.setPadding(48, 48, 48, 48);
        status.setTextSize(16);
        setContentView(status);

        if (new File(assetsDir(this), MARKER).exists()) {
            startGame();
            return;
        }
        status.setOnClickListener(v -> pickFolder());
        pickFolder();
    }

    private void pickFolder() {
        status.setText("Elegí la carpeta de South Park Rally (la versión de PC) para importar los assets.\n\nToca acá para abrir el selector de nuevo.");
        startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE), REQ_TREE);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != REQ_TREE || resultCode != RESULT_OK || data == null || data.getData() == null) {
            return;  // canceló: el texto permite reintentar tocando la pantalla
        }
        final Uri tree = data.getData();
        status.setOnClickListener(null);
        new Thread(() -> {
            try {
                DocumentFile root = DocumentFile.fromTreeUri(this, tree);
                if (root == null) throw new IOException("No se pudo abrir la carpeta");
                File dest = assetsDir(this);
                dest.mkdirs();
                copied = 0;
                copyTree(root, dest);
                new File(dest, MARKER).createNewFile();
                runOnUiThread(this::startGame);
            } catch (IOException e) {
                runOnUiThread(() -> {
                    status.setText("Error al importar: " + e.getMessage() + "\n\nToca para reintentar.");
                    status.setOnClickListener(v -> pickFolder());
                });
            }
        }).start();
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
                copyFile(child.getUri(), target);
                copied++;
                if (copied % 20 == 0) {
                    final int n = copied;
                    runOnUiThread(() -> status.setText("Importando… " + n + " archivos"));
                }
            }
        }
    }

    private void copyFile(Uri src, File target) throws IOException {
        try (InputStream in = getContentResolver().openInputStream(src);
             OutputStream out = new FileOutputStream(target)) {
            if (in == null) throw new IOException("No se pudo leer " + target.getName());
            byte[] buf = new byte[64 * 1024];
            int n;
            while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
        }
    }

    private void startGame() {
        startActivity(new Intent(this, GameActivity.class));
        finish();
    }
}
