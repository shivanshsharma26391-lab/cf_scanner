[app]
title = CF Scanner
package.name = cfscanner
package.domain = org.cfscanner
source.dir = .
source.include_exts = py
version = 1.0
requirements = python3,kivy
p4a.branch = 2022.09.04
orientation = portrait
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.allow_backup = True
fullscreen = 0
android.presplash_color = #0d1117

[buildozer]
log_level = 2
warn_on_root = 1
