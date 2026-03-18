[aplicación]
título = Chat-Isis-Y-marcos
nombre.del.paquete = isisymarcos
paquete.dominio = org.isisymarcos

directorio.source = .
source.include_exts = py,png,jpg,kv,atlas

versión = 1.0

Requisitos = Python 3, Kivy, KivyMD, Requests

orientación = vertical
pantalla completa = 0

android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.api = 31
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True

android.arch = arm64-v8a

p4a.bootstrap = sdl2

[buildozer]
log_level = 2
advertir_en_raíz = 1
