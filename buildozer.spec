[app]
title = mini
package.name = mini
package.domain = org.mini
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,java
version = 1.0
requirements = python3,kivy==2.3.0,pyjnius,android,certifi
orientation = portrait
fullscreen = 1
android.permissions = INTERNET, RECORD_AUDIO, CALL_PHONE, READ_CONTACTS, SEND_SMS, READ_PHONE_STATE, READ_CALL_LOG, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE
android.api = 31
android.minapi = 24
android.ndk = 25b
android.ndk_api = 24
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = True
android.extra_manifest_xml = ./extra_manifest.xml

# Pin p4a to a stable release
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
