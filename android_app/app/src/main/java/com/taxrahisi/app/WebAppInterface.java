package com.taxrahisi.app;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Vibrator;
import android.webkit.JavascriptInterface;
import android.widget.Toast;

public class WebAppInterface {
    private final Activity activity;

    public WebAppInterface(Activity activity) {
        this.activity = activity;
    }

    @JavascriptInterface
    public void showToast(final String message) {
        activity.runOnUiThread(new Runnable() {
            @Override
            public void run() {
                Toast.makeText(activity, message, Toast.LENGTH_SHORT).show();
            }
        });
    }

    @JavascriptInterface
    public void dialUssd(final String ussdCode) {
        activity.runOnUiThread(new Runnable() {
            @Override
            public void run() {
                try {
                    String encodedHash = Uri.encode(ussdCode);
                    Intent intent = new Intent(Intent.ACTION_DIAL, Uri.parse("tel:" + encodedHash));
                    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                    activity.startActivity(intent);
                } catch (Exception e) {
                    Toast.makeText(activity, "Imeshindwa kupiga USSD: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                }
            }
        });
    }

    @JavascriptInterface
    public void shareText(final String title, final String content) {
        activity.runOnUiThread(new Runnable() {
            @Override
            public void run() {
                try {
                    Intent shareIntent = new Intent(Intent.ACTION_SEND);
                    shareIntent.setType("text/plain");
                    shareIntent.putExtra(Intent.EXTRA_SUBJECT, title);
                    shareIntent.putExtra(Intent.EXTRA_TEXT, content);
                    activity.startActivity(Intent.createChooser(shareIntent, title));
                } catch (Exception e) {
                    Toast.makeText(activity, "Kushiriki kumeshindwa", Toast.LENGTH_SHORT).show();
                }
            }
        });
    }

    @JavascriptInterface
    public void vibrate(final long milliseconds) {
        try {
            Vibrator v = (Vibrator) activity.getSystemService(Context.VIBRATOR_SERVICE);
            if (v != null && v.hasVibrator()) {
                v.vibrate(milliseconds);
            }
        } catch (Exception ignored) {
        }
    }

    @JavascriptInterface
    public boolean isNativeApp() {
        return true;
    }

    @JavascriptInterface
    public String getAppVersion() {
        return "1.0.0 (TaxRahisi Mobile)";
    }
}
