import 'package:permission_handler/permission_handler.dart';

/// Thin wrapper around permission_handler's camera permission, matching the
/// codebase's existing thin-service pattern (see BiometricAuthService).
class CameraPermissionService {
  /// Requests camera access if not already granted. Returns true if the
  /// camera can be used. `permanentlyDenied` is set when the OS will no
  /// longer show its own prompt — the caller should point the operator at
  /// Settings instead of retrying the request.
  static Future<CameraPermissionResult> ensureGranted() async {
    var status = await Permission.camera.status;
    if (status.isGranted) {
      return const CameraPermissionResult(
        granted: true,
        permanentlyDenied: false,
      );
    }
    if (status.isPermanentlyDenied) {
      return const CameraPermissionResult(
        granted: false,
        permanentlyDenied: true,
      );
    }

    status = await Permission.camera.request();
    return CameraPermissionResult(
      granted: status.isGranted,
      permanentlyDenied: status.isPermanentlyDenied,
    );
  }

  static Future<void> openSettings() => openAppSettings();
}

class CameraPermissionResult {
  final bool granted;
  final bool permanentlyDenied;
  const CameraPermissionResult({
    required this.granted,
    required this.permanentlyDenied,
  });
}
