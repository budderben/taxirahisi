#!/usr/bin/env bash
set -e

# ==============================================================================
# TaxRahisi Android APK Build Script
# Compiles native Android application using verified local Debian/Android SDK tools
# ==============================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=========================================================="
echo "  Building TaxRahisi Android APK (com.taxrahisi.app)"
echo "=========================================================="

# Locate SDK dependencies
ANDROID_JAR="/home/ben/.gradle/caches/8.11.1/transforms/6114e045d9df78f5443848ab03e7c78d/transformed/android.jar"
if [ ! -f "$ANDROID_JAR" ]; then
    ANDROID_JAR=$(find /home/ben/.gradle/caches -name "android.jar" 2>/dev/null | head -n 1)
fi

FRAMEWORK_RES="/usr/share/android-framework-res/framework-res.apk"
DX_JAR="/usr/share/dex2jar/lib/dx-23.0.0.jar"
AAPT="/bin/aapt"
ZIPALIGN="/bin/zipalign"
APKSIGNER="/bin/apksigner"
KEYTOOL="/bin/keytool"

echo "Using Android Jar:      $ANDROID_JAR"
echo "Using Framework Res:    $FRAMEWORK_RES"
echo "Using DX Compiler:      $DX_JAR"
echo "Using AAPT:             $AAPT"

# Clean build directory
BUILD_DIR="$PROJECT_DIR/build"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/gen" "$BUILD_DIR/bin"

# 1. Generate R.java with AAPT
echo "==> Step 1/7: Generating R.java from resources..."
$AAPT package -f -m \
    -J "$BUILD_DIR/gen" \
    -M "$PROJECT_DIR/app/src/main/AndroidManifest.xml" \
    -S "$PROJECT_DIR/app/src/main/res" \
    -I "$FRAMEWORK_RES"

# 2. Compile Java sources
echo "==> Step 2/7: Compiling Java classes with javac..."
javac --release 8 \
    -cp "$ANDROID_JAR:$BUILD_DIR/gen" \
    -d "$BUILD_DIR/bin" \
    "$BUILD_DIR/gen/com/taxrahisi/app/R.java" \
    "$PROJECT_DIR/app/src/main/java/com/taxrahisi/app/"*.java

# 3. Patch bytecode version header for Dalvik dx compatibility
echo "==> Step 3/7: Patching classfile version for Dalvik dx compatibility..."
python3 -c '
import os

bin_dir = "'"$BUILD_DIR/bin"'"
count = 0
for root, _, files in os.walk(bin_dir):
    for f in files:
        if f.endswith(".class"):
            path = os.path.join(root, f)
            with open(path, "r+b") as fp:
                data = fp.read(8)
                if len(data) >= 8 and data[0:4] == b"\xca\xfe\xba\xbe":
                    major = data[7]
                    if major > 51:
                        fp.seek(7)
                        fp.write(bytes([51]))
                        count += 1
print(f"Patched {count} class files to Java 7 bytecode for dx.")
'

# 4. Convert classes to classes.dex with dx
echo "==> Step 4/7: Compiling classes to DEX bytecode (classes.dex)..."
java -jar "$DX_JAR" --dex --output="$BUILD_DIR/classes.dex" "$BUILD_DIR/bin"

# 5. Package Android resources, manifest, and assets
echo "==> Step 5/7: Packaging APK resources and web assets with AAPT..."
$AAPT package -f \
    -M "$PROJECT_DIR/app/src/main/AndroidManifest.xml" \
    -S "$PROJECT_DIR/app/src/main/res" \
    -A "$PROJECT_DIR/app/src/main/assets" \
    -I "$FRAMEWORK_RES" \
    -F "$BUILD_DIR/unaligned_raw.apk"

# Add classes.dex into the APK package
cd "$BUILD_DIR"
$AAPT add "unaligned_raw.apk" "classes.dex"
cd "$PROJECT_DIR"

# 6. Zip-align the APK package on 4-byte boundaries
echo "==> Step 6/7: Aligning APK on 4-byte boundaries with zipalign..."
$ZIPALIGN -v -f 4 "$BUILD_DIR/unaligned_raw.apk" "$BUILD_DIR/TaxRahisi-unaligned.apk"

# 7. Sign APK with debug keystore
echo "==> Step 7/7: Signing APK with apksigner..."
KEYSTORE="$PROJECT_DIR/taxrahisi-debug.keystore"
if [ ! -f "$KEYSTORE" ]; then
    echo "Creating debug keystore..."
    $KEYTOOL -genkeypair -validity 10000 \
        -dname "CN=TaxRahisi, OU=TRA Innovation, O=United Republic of Tanzania, C=TZ" \
        -keystore "$KEYSTORE" \
        -storepass android -keypass android \
        -alias androiddebugkey -keyalg RSA -keysize 2048
fi

FINAL_APK="$PROJECT_DIR/TaxRahisi.apk"
rm -f "$FINAL_APK"

$APKSIGNER sign \
    --ks "$KEYSTORE" \
    --ks-pass pass:android \
    --key-pass pass:android \
    --ks-key-alias androiddebugkey \
    --out "$FINAL_APK" \
    "$BUILD_DIR/TaxRahisi-unaligned.apk"

echo "=========================================================="
echo "  Verifying signed APK..."
echo "=========================================================="
$APKSIGNER verify -v "$FINAL_APK"

echo ""
echo "APK Summary:"
$AAPT dump badging "$FINAL_APK" | head -n 12

echo ""
echo "=========================================================="
echo "  BUILD SUCCESSFUL!"
echo "  Output APK: $FINAL_APK"
echo "  Size: $(du -h "$FINAL_APK" | cut -f1)"
echo "=========================================================="
