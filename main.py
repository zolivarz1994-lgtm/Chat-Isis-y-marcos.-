# ============================================================
# Chat Isis y Marcos - APK para Android
# ============================================================
# buildozer.spec ya incluye todos los permisos necesarios
# ============================================================

import hashlib
import json
import time
import requests
from threading import Thread

from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDIconButton, MDRaisedButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.snackbar import Snackbar

Window.softinput_mode = "below_target"

# ============================================================
# FIREBASE
# ============================================================
DB_URL = "https://chat-isis-y-marcos-default-rtdb.firebaseio.com"


def hash_clave(clave):
    return hashlib.sha256(clave.encode()).hexdigest()


def obtener_usuario(nombre):
    try:
        r = requests.get(f"{DB_URL}/usuarios/{nombre}.json", timeout=8)
        return r.json()
    except Exception:
        return None


def guardar_usuario(nombre, datos):
    try:
        requests.put(f"{DB_URL}/usuarios/{nombre}.json", json=datos, timeout=8)
        return True
    except Exception:
        return False


def enviar_mensaje(remitente, texto):
    try:
        requests.post(f"{DB_URL}/mensajes.json", json={
            "texto": texto,
            "remitente": remitente,
            "timestamp": int(time.time() * 1000),
        }, timeout=8)
    except Exception:
        pass


# ============================================================
# FIREBASE SSE - Escucha en tiempo real
# ============================================================
_streaming_activo = False


def iniciar_streaming(on_mensajes):
    global _streaming_activo
    _streaming_activo = True

    def _hilo():
        url = f"{DB_URL}/mensajes.json"
        headers = {"Accept": "text/event-stream", "Cache-Control": "no-cache"}
        while _streaming_activo:
            try:
                with requests.get(url, headers=headers, stream=True, timeout=300) as r:
                    event_type = None
                    for linea in r.iter_lines():
                        if not _streaming_activo:
                            return
                        if not linea:
                            continue
                        if isinstance(linea, bytes):
                            linea = linea.decode("utf-8")
                        if linea.startswith("event:"):
                            event_type = linea[6:].strip()
                        elif linea.startswith("data:"):
                            try:
                                payload = json.loads(linea[5:].strip())
                                datos = payload.get("data")
                                if datos and isinstance(datos, dict):
                                    msgs = []
                                    for key, val in datos.items():
                                        if isinstance(val, dict):
                                            val["id"] = key
                                            msgs.append(val)
                                    msgs.sort(key=lambda x: x.get("timestamp", 0))
                                    Clock.schedule_once(lambda dt, m=msgs: on_mensajes(m), 0)
                            except Exception:
                                pass
            except Exception:
                if _streaming_activo:
                    time.sleep(5)

    Thread(target=_hilo, daemon=True).start()


def detener_streaming():
    global _streaming_activo
    _streaming_activo = False


# ============================================================
# WIDGET DE MENSAJE
# ============================================================
ANCHO_MSG = 290


def crear_widget_mensaje(texto, remitente, hora, es_mio):
    ancho_px = dp(ANCHO_MSG - 24)

    core = CoreLabel(font_size=sp(14))
    core.text = texto
    core.text_size = (ancho_px, None)
    core.refresh()
    texto_alto = core.texture.size[1] + dp(4)

    alto_total = dp(18) + texto_alto + dp(18) + dp(20)

    fila = BoxLayout(
        orientation="horizontal",
        size_hint_y=None,
        height=alto_total,
        padding=[dp(6), dp(3)],
    )

    if es_mio:
        fila.add_widget(Widget(size_hint_x=0.08))

    caja = BoxLayout(
        orientation="vertical",
        size_hint=(None, None),
        width=dp(ANCHO_MSG),
        height=alto_total - dp(6),
        padding=[dp(10), dp(8)],
        spacing=dp(2),
    )

    # Burbuja verde menta para mensajes propios, blanca para el otro
    color_fondo = (0.78, 0.97, 0.87, 1) if es_mio else (0.96, 0.96, 0.96, 1)
    with caja.canvas.before:
        Color(*color_fondo)
        rect = RoundedRectangle(pos=caja.pos, size=caja.size, radius=[dp(12)])

    def _upd_rect(inst, val):
        rect.pos = inst.pos
        rect.size = inst.size

    caja.bind(pos=_upd_rect, size=_upd_rect)

    # Nombre: teal oscuro para propios, azul oscuro para el otro
    color_nombre = (0.0, 0.5, 0.35, 1) if es_mio else (0.1, 0.4, 0.75, 1)
    caja.add_widget(Label(
        text="Tu" if es_mio else remitente.capitalize(),
        color=color_nombre,
        font_size=sp(12),
        size_hint_y=None,
        height=dp(18),
        halign="left",
        valign="middle",
        text_size=(ancho_px, None),
        bold=True,
    ))

    # Texto del mensaje en negro para que se vea sobre el fondo claro
    caja.add_widget(Label(
        text=texto,
        color=(0.08, 0.08, 0.08, 1),
        font_size=sp(14),
        size_hint_y=None,
        height=texto_alto,
        halign="left",
        valign="top",
        text_size=(ancho_px, None),
    ))

    # Hora en gris oscuro
    caja.add_widget(Label(
        text=hora,
        color=(0.4, 0.4, 0.4, 1),
        font_size=sp(11),
        size_hint_y=None,
        height=dp(18),
        halign="right",
        valign="middle",
        text_size=(ancho_px, None),
    ))

    fila.add_widget(caja)

    if not es_mio:
        fila.add_widget(Widget(size_hint_x=0.08))

    return fila


# ============================================================
# CAMPO DE CONTRASENA CON OJITO
# ============================================================
class CampoContrasena(BoxLayout):
    def __init__(self, hint_text="Clave", **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint = (0.92, None)
        self.height = dp(56)
        self.pos_hint = {"center_x": 0.5}
        self.spacing = dp(2)

        self.campo = MDTextField(
            hint_text=hint_text,
            password=True,
            mode="rectangle",
            multiline=False,
        )
        self.btn = MDIconButton(
            icon="eye",
            size_hint=(None, 1),
            width=dp(48),
            on_release=self._toggle,
        )
        self.add_widget(self.campo)
        self.add_widget(self.btn)

    def _toggle(self, *args):
        self.campo.password = not self.campo.password
        self.btn.icon = "eye-off" if not self.campo.password else "eye"

    @property
    def text(self):
        return self.campo.text

    @text.setter
    def text(self, value):
        self.campo.text = value


# ============================================================
# PANTALLA 1: ELEGIR USUARIO
# ============================================================
class PantallaEleccion(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            Color(0, 0, 0, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda i, v: setattr(self._bg, 'pos', v),
                  size=lambda i, v: setattr(self._bg, 'size', v))

        layout = MDBoxLayout(orientation="vertical", padding=dp(30), spacing=dp(18))
        layout.add_widget(Widget(size_hint_y=0.2))
        layout.add_widget(Label(
            text="Isis y Marcos",
            color=(1, 1, 1, 1), font_size=sp(30), bold=True,
            size_hint_y=None, height=dp(50),
        ))
        layout.add_widget(Label(
            text="Chat privado entre los dos",
            color=(0.7, 0.85, 0.85, 1), font_size=sp(15),
            size_hint_y=None, height=dp(30),
        ))
        layout.add_widget(Widget(size_hint_y=0.08))
        layout.add_widget(Label(
            text="Quien eres tu?",
            color=(0.75, 0.85, 0.85, 1), font_size=sp(15),
            size_hint_y=None, height=dp(30),
        ))
        layout.add_widget(MDRaisedButton(
            text="  Isis  ", font_size="18sp",
            size_hint=(None, None), size=(dp(200), dp(55)),
            pos_hint={"center_x": 0.5}, md_bg_color=(0, 0.66, 0.52, 1),
            on_release=lambda x: self.elegir("isis"),
        ))
        layout.add_widget(MDRaisedButton(
            text="  Marcos  ", font_size="18sp",
            size_hint=(None, None), size=(dp(200), dp(55)),
            pos_hint={"center_x": 0.5}, md_bg_color=(0.11, 0.56, 0.96, 1),
            on_release=lambda x: self.elegir("marcos"),
        ))
        layout.add_widget(Widget(size_hint_y=0.3))
        self.add_widget(layout)

    def elegir(self, usuario):
        MDApp.get_running_app().usuario_actual = usuario
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = "login"


# ============================================================
# PANTALLA 2: LOGIN
# ============================================================
class PantallaLogin(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.campo_clave = None
        self.campo_confirmar = None
        self.lbl_error = None

    def on_enter(self):
        self.clear_widgets()

        with self.canvas.before:
            Color(0, 0, 0, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda i, v: setattr(self._bg, 'pos', v),
                  size=lambda i, v: setattr(self._bg, 'size', v))

        app = MDApp.get_running_app()
        usuario = app.usuario_actual
        nombre = usuario.capitalize()

        raiz = MDBoxLayout(orientation="vertical")
        raiz.add_widget(MDTopAppBar(
            title=f"Acceso - {nombre}",
            left_action_items=[["arrow-left", lambda x: self._volver()]],
        ))
        self.contenido = MDBoxLayout(orientation="vertical", padding=dp(24), spacing=dp(14))
        raiz.add_widget(self.contenido)
        self.add_widget(raiz)

        Thread(target=self._verificar, args=(usuario, nombre), daemon=True).start()

    def _verificar(self, usuario, nombre):
        datos = obtener_usuario(usuario)
        Clock.schedule_once(lambda dt: self._mostrar(datos, usuario, nombre), 0)

    def _mostrar(self, datos, usuario, nombre):
        self.contenido.clear_widgets()
        self.contenido.add_widget(Widget(size_hint_y=0.1))

        es_nuevo = datos is None or "clave" not in datos
        texto = (
            f"Hola {nombre}!\nPrimera vez aqui.\nCrea tu clave personal:"
            if es_nuevo else
            f"Bienvenid@ {nombre}!\nIngresa tu clave:"
        )
        self.contenido.add_widget(Label(
            text=texto, color=(1, 1, 1, 1), font_size=sp(16),
            halign="center", size_hint_y=None, height=dp(90),
            text_size=(dp(300), None),
        ))

        self.campo_clave = CampoContrasena(hint_text="Clave")
        self.contenido.add_widget(self.campo_clave)

        if es_nuevo:
            self.campo_confirmar = CampoContrasena(hint_text="Confirmar clave")
            self.contenido.add_widget(self.campo_confirmar)
        else:
            self.campo_confirmar = None

        self.contenido.add_widget(MDRaisedButton(
            text="Crear clave y entrar" if es_nuevo else "Entrar al chat",
            size_hint=(None, None), size=(dp(220), dp(50)),
            pos_hint={"center_x": 0.5}, md_bg_color=(0, 0.66, 0.52, 1),
            on_release=lambda x: self._ingresar(datos, usuario, es_nuevo),
        ))

        self.lbl_error = Label(
            text="", color=(1, 0.4, 0.4, 1), font_size=sp(14),
            halign="center", size_hint_y=None, height=dp(40),
            text_size=(dp(300), None),
        )
        self.contenido.add_widget(self.lbl_error)
        self.contenido.add_widget(Widget())

    def _ingresar(self, datos_actuales, usuario, es_nuevo):
        clave = self.campo_clave.text.strip()
        if not clave:
            self.lbl_error.text = "Por favor escribe tu clave."
            return
        if es_nuevo:
            confirmar = self.campo_confirmar.text.strip() if self.campo_confirmar else ""
            if clave != confirmar:
                self.lbl_error.text = "Las claves no coinciden."
                self.campo_clave.text = ""
                if self.campo_confirmar:
                    self.campo_confirmar.text = ""
                return
            if len(clave) < 4:
                self.lbl_error.text = "Minimo 4 caracteres."
                self.campo_clave.text = ""
                if self.campo_confirmar:
                    self.campo_confirmar.text = ""
                return
            Thread(
                target=lambda: (
                    guardar_usuario(usuario, {"clave": hash_clave(clave)}),
                    Clock.schedule_once(lambda dt: self._ir_al_chat(), 0)
                ),
                daemon=True
            ).start()
        else:
            if hash_clave(clave) != datos_actuales.get("clave", ""):
                self.lbl_error.text = "Clave incorrecta. Intenta de nuevo."
                self.campo_clave.text = ""
                return
            self._ir_al_chat()

    def _ir_al_chat(self):
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = "chat"

    def _volver(self):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "eleccion"


# ============================================================
# PANTALLA 3: CHAT
# ============================================================
class PantallaChat(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ids_vistos = set()
        self.dialog_clave = None
        self.contenedor = None
        self.scroll = None

    def on_enter(self):
        self._construir_ui()
        iniciar_streaming(self._on_mensajes)

    def on_leave(self):
        detener_streaming()

    def _construir_ui(self):
        self.clear_widgets()
        self.ids_vistos.clear()

        with self.canvas.before:
            Color(0, 0, 0, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda i, v: setattr(self._bg, 'pos', v),
                  size=lambda i, v: setattr(self._bg, 'size', v))

        app = MDApp.get_running_app()
        otro = "Marcos" if app.usuario_actual == "isis" else "Isis"

        raiz = BoxLayout(orientation="vertical")

        raiz.add_widget(MDTopAppBar(
            title=f"Chat con {otro}",
            left_action_items=[["logout", lambda x: self._salir()]],
            right_action_items=[["key-variant", lambda x: self._cambiar_clave()]],
        ))

        self.scroll = ScrollView(do_scroll_x=False)
        from kivy.uix.gridlayout import GridLayout
        self.contenedor = GridLayout(
            cols=1,
            size_hint_y=None,
            spacing=dp(4),
            padding=[dp(4), dp(6)],
        )
        self.contenedor.bind(
            minimum_height=self.contenedor.setter('height')
        )
        self.scroll.add_widget(self.contenedor)
        raiz.add_widget(self.scroll)

        barra = BoxLayout(
            orientation="horizontal",
            size_hint_y=None, height=dp(62),
            padding=[dp(8), dp(8)], spacing=dp(6),
        )
        with barra.canvas.before:
            Color(0.05, 0.05, 0.05, 1)
            self._bg_barra = Rectangle(pos=barra.pos, size=barra.size)
        barra.bind(
            pos=lambda i, v: setattr(self._bg_barra, 'pos', v),
            size=lambda i, v: setattr(self._bg_barra, 'size', v),
        )

        self.campo_texto = MDTextField(
            hint_text="Escribe un mensaje...",
            mode="rectangle", multiline=False,
            size_hint_y=None, height=dp(46),
        )
        barra.add_widget(self.campo_texto)
        barra.add_widget(MDRaisedButton(
            text=">", font_size="18sp",
            size_hint=(None, None), size=(dp(52), dp(46)),
            md_bg_color=(0, 0.66, 0.52, 1),
            on_release=lambda x: self._enviar(),
        ))
        raiz.add_widget(barra)
        self.add_widget(raiz)

    def _on_mensajes(self, mensajes):
        app = MDApp.get_running_app()
        usuario = app.usuario_actual
        nuevos = False

        for msg in mensajes:
            mid = msg.get("id", "")
            if mid in self.ids_vistos:
                continue
            self.ids_vistos.add(mid)

            ts = msg.get("timestamp", 0)
            hora = ""
            if ts:
                t = time.localtime(ts / 1000)
                hora = f"{t.tm_hour:02d}:{t.tm_min:02d}"

            w = crear_widget_mensaje(
                texto=msg.get("texto", ""),
                remitente=msg.get("remitente", ""),
                hora=hora,
                es_mio=(msg.get("remitente", "") == usuario),
            )
            self.contenedor.add_widget(w)
            nuevos = True

        if nuevos:
            Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.1)

    def _enviar(self):
        texto = self.campo_texto.text.strip()
        if not texto:
            return
        self.campo_texto.text = ""
        app = MDApp.get_running_app()
        Thread(target=enviar_mensaje, args=(app.usuario_actual, texto), daemon=True).start()

    def _salir(self):
        MDApp.get_running_app().usuario_actual = None
        self.ids_vistos.clear()
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "eleccion"

    def _cambiar_clave(self):
        self.f_actual = CampoContrasena(hint_text="Clave actual")
        self.f_nueva = CampoContrasena(hint_text="Nueva clave")
        self.f_conf = CampoContrasena(hint_text="Confirmar nueva clave")
        self.lbl_err = Label(
            text="", color=(1, 0.4, 0.4, 1), font_size=sp(13),
            halign="center", size_hint_y=None, height=dp(36),
            text_size=(dp(260), None),
        )
        contenido = MDBoxLayout(
            orientation="vertical", spacing=dp(10),
            size_hint_y=None, height=dp(265),
        )
        contenido.add_widget(self.f_actual)
        contenido.add_widget(self.f_nueva)
        contenido.add_widget(self.f_conf)
        contenido.add_widget(self.lbl_err)

        self.dialog_clave = MDDialog(
            title="Cambiar mi clave",
            type="custom",
            content_cls=contenido,
            buttons=[
                MDFlatButton(text="CANCELAR", on_release=lambda x: self.dialog_clave.dismiss()),
                MDRaisedButton(
                    text="GUARDAR", md_bg_color=(0, 0.66, 0.52, 1),
                    on_release=lambda x: self._guardar_clave(),
                ),
            ],
        )
        self.dialog_clave.open()

    def _guardar_clave(self):
        actual = self.f_actual.text.strip()
        nueva = self.f_nueva.text.strip()
        conf = self.f_conf.text.strip()

        if not actual or not nueva or not conf:
            self.lbl_err.text = "Completa todos los campos."
            return
        if nueva != conf:
            self.lbl_err.text = "Las claves nuevas no coinciden."
            self.f_nueva.text = ""
            self.f_conf.text = ""
            return
        if len(nueva) < 4:
            self.lbl_err.text = "Minimo 4 caracteres."
            return

        app = MDApp.get_running_app()
        usuario = app.usuario_actual

        def _v():
            datos = obtener_usuario(usuario)
            if datos is None or hash_clave(actual) != datos.get("clave", ""):
                Clock.schedule_once(lambda dt: setattr(self.lbl_err, "text", "Clave actual incorrecta."), 0)
                Clock.schedule_once(lambda dt: setattr(self.f_actual, "text", ""), 0)
                return
            datos["clave"] = hash_clave(nueva)
            guardar_usuario(usuario, datos)
            Clock.schedule_once(lambda dt: (self.dialog_clave.dismiss(), Snackbar(text="Clave cambiada!").open()), 0)

        Thread(target=_v, daemon=True).start()


# ============================================================
# APP PRINCIPAL
# ============================================================
class ChatApp(MDApp):
    usuario_actual = None

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Teal"
        self.title = "Isis y Marcos"
        self.icon = "icon.png"

        sm = ScreenManager()
        sm.add_widget(PantallaEleccion(name="eleccion"))
        sm.add_widget(PantallaLogin(name="login"))
        sm.add_widget(PantallaChat(name="chat"))
        sm.current = "eleccion"
        return sm


if __name__ == "__main__":
    ChatApp().run()
