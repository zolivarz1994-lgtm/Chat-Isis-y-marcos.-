[app]
title = Chat-Isis-y-marcos
package.name = isisymarcos
package.domain = org.isisymarcos

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 1.0

requirements = python3, kivy, kivymd, requests

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.api = 31
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True

android.arch = arm64-v8a

p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1
