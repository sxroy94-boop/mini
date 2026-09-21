[app]
title = mini
package.name = mini
package.domain = org.mini
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0
requirements = python3,kivy==2.3.0
orientation = portrait
fullscreen = 1
android.permissions = INTERNET, RECORD_AUDIO, CALL_PHONE, READ_CONTACTS, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE
android.api = 31
android.minapi = 24
android.ndk = 25b
android.ndk_api = 24
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = True

# Pin p4a to a stable release (this is what fixes the Python 3.14 problem)
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
