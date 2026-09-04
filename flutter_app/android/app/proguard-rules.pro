# Flutter's own embedding classes are referenced from native/JNI code, not
# just Dart->platform channel calls, so R8 can't see the real usage and
# would otherwise strip them under -isMinifyEnabled.
-keep class io.flutter.app.** { *; }
-keep class io.flutter.plugin.**  { *; }
-keep class io.flutter.util.**  { *; }
-keep class io.flutter.view.**  { *; }
-keep class io.flutter.**  { *; }
-keep class io.flutter.plugins.**  { *; }

# camera / CameraX: internal classes are looked up by fully-qualified name
# from native code (Camera2/CameraX interop), which R8's static analysis
# can't trace — stripping or renaming them breaks camera init at runtime
# with no compile-time warning.
-keep class androidx.camera.** { *; }
-dontwarn androidx.camera.**

# local_auth's BiometricPrompt integration + flutter_secure_storage's
# Android Keystore/EncryptedSharedPreferences path both rely on
# reflection-based provider lookups.
-keep class androidx.biometric.** { *; }
-keep class androidx.security.crypto.** { *; }

# sqflite invokes SQLite via JNI method signatures matched by name.
-keep class org.sqlite.** { *; }
-keep class io.flutter.plugins.sqflite.** { *; }

# Gson/JSON model classes used by any plugin via reflection-based
# (de)serialization should keep their field names.
-keepattributes Signature
-keepattributes *Annotation*
-keepattributes EnclosingMethod
-keepattributes InnerClasses

# Flutter's embedding always references Play Core's deferred-components/
# split-install API (FlutterPlayStoreSplitApplication,
# PlayStoreDeferredComponentManager) regardless of whether the app
# actually uses dynamic feature delivery — this app doesn't, and the
# com.google.android.play:core dependency isn't pulled in at all, so R8
# can't resolve those classes and fails the build without being told
# they're intentionally absent. This is Flutter's own documented
# workaround, not an app-specific hack:
# https://docs.flutter.dev/release/breaking-changes/deferred-components-play-core-migration
-dontwarn com.google.android.play.core.**
