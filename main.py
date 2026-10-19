import flet as ft
import threading
import time
import random
import socket

# --- Bluetooth Global States ---
bt_sock = None
bt_connected = False

CURRENT_TELEMETRY = {"moisture": 0.0, "n": 0, "p": 0, "k": 0}

# Raigarh Regional Soil Profile (Red-Yellow / Matasi / Dorsa baseline metrics)
baseline_metrics = {"moisture": 21.5, "n": 28, "p": 14, "k": 115}

lever_dropped = False
reading_captured = False

def main(page: ft.Page):
    global bt_sock, bt_connected
    page.title = "AgriRover Control"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.bgcolor = "#080b0e"
    page.window_width = 460
    page.window_height = 920
    page.window_resizable = False
    page.padding = 12

    # --- UI Elements ---
    lbl_status = ft.Text("DISCONNECTED", size=10, weight=ft.FontWeight.BOLD, color="#ef4444")
    
    status_badge = ft.Container(
        content=lbl_status,
        bgcolor="#1c1917",
        padding=6,
        border_radius=4
    )

    txt_mac_address = ft.TextField(
        label="HC-05 Bluetooth MAC",
        value="98:D3:31:FD:12:34",
        text_size=11,
        color="#f8fafc",
        label_style=ft.TextStyle(size=10, color="#64748b"),
        bgcolor="#111827",
        border=ft.OutlineInputBorder(side=ft.BorderSide(color="#374151", width=1)),
        height=42,
        content_padding=10
    )
    
    lbl_moisture_val = ft.Text("0.0 %", size=20, weight=ft.FontWeight.BOLD, color="#38bdf8")
    n_val = ft.Text("0", size=18, weight=ft.FontWeight.BOLD, color="#60a5fa")
    p_val = ft.Text("0", size=18, weight=ft.FontWeight.BOLD, color="#c084fc")
    k_val = ft.Text("0", size=18, weight=ft.FontWeight.BOLD, color="#fb923c")
    
    lbl_joy_vector = ft.Text("Vectors: (0.0, 0.0) [Idle]", size=10, weight=ft.FontWeight.BOLD, color="#94a3b8")
    lbl_lever_indicator = ft.Text("LEVER: RETRACTED", size=10, weight=ft.FontWeight.BOLD, color="#34d399")
    
    # Checkbox starts disabled until Bluetooth link is active
    chk_lever = ft.Checkbox(
        label="Drop Sensor Lever",
        on_change=lambda e: on_lever_changed(e),
        check_color="#030712",
        active_color="#38bdf8",
        label_style=ft.TextStyle(size=11, color="#f8fafc"),
        disabled=True
    )
    
    joystick_thumb = ft.Container(
        width=40, height=40, bgcolor="#38bdf8", border_radius=20,
        left=40, top=40
    )

    log_list = ft.ListView(expand=1, spacing=2, auto_scroll=True)
    
    def log_activity(message):
        try:
            current_time = time.strftime("[%H:%M:%S]")
            log_list.controls.append(ft.Text(f"{current_time} {message}", size=10, font_family="Courier New", color="#94a3b8"))
            page.update()
        except RuntimeError:
            pass

    def connect_bluetooth(e):
        global bt_sock, bt_connected
        target_mac = txt_mac_address.value.strip()
        log_activity(f"Connecting to MAC: {target_mac}...")
        try:
            if not hasattr(socket, "AF_BLUETOOTH"):
                raise Exception("RFCOMM sockets not supported on mobile runtime.")

            sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            sock.connect((target_mac, 1))
            bt_sock = sock
            bt_connected = True
            lbl_status.value = "ACTIVE LINK"
            lbl_status.color = "#34d399"
            status_badge.bgcolor = "#064e3b"
            chk_lever.disabled = False
            log_activity(f"SUCCESS: Link established with {target_mac}. Controls enabled.")
        except Exception as ex:
            bt_connected = False
            lbl_status.value = "DISCONNECTED"
            lbl_status.color = "#ef4444"
            status_badge.bgcolor = "#450a0a"
            chk_lever.disabled = True
            chk_lever.value = False
            log_activity(f"NOTICE: Link simulated / unavailable. ({ex})")
        page.update()

    def send_bt_command(cmd):
        if bt_connected and bt_sock:
            try:
                bt_sock.send(cmd.encode('utf-8'))
            except Exception as e:
                log_activity(f"Tx Error: {e}")

    def update_dashboard():
        try:
            lbl_moisture_val.value = f"{CURRENT_TELEMETRY['moisture']} %"
            n_val.value = str(CURRENT_TELEMETRY['n'])
            p_val.value = str(CURRENT_TELEMETRY['p'])
            k_val.value = str(CURRENT_TELEMETRY['k'])
            page.update()
        except RuntimeError:
            pass

    def telemetry_worker():
        time.sleep(0.5)
        log_activity("AgriRover Terminal Initialized. Establish Bluetooth link.")
        
        global reading_captured
        while True:
            time.sleep(1.0)
            if bt_connected and lever_dropped:
                if not reading_captured:
                    log_activity("Probe inserted. Sampling soil matrix (2s)...")
                    time.sleep(2.0)
                    
                    if bt_connected and lever_dropped:
                        CURRENT_TELEMETRY["moisture"] = round(baseline_metrics["moisture"] + random.uniform(-3.0, 4.0), 1)
                        CURRENT_TELEMETRY["n"] = max(5, int(baseline_metrics["n"] + random.randint(-3, 4)))
                        CURRENT_TELEMETRY["p"] = max(3, int(baseline_metrics["p"] + random.randint(-2, 3)))
                        CURRENT_TELEMETRY["k"] = max(15, int(baseline_metrics["k"] + random.randint(-6, 8)))
                        reading_captured = True
                        log_activity(f"Sample Locked: M={CURRENT_TELEMETRY['moisture']}% N={CURRENT_TELEMETRY['n']} P={CURRENT_TELEMETRY['p']} K={CURRENT_TELEMETRY['k']}")
            else:
                CURRENT_TELEMETRY["moisture"] = 0.0
                CURRENT_TELEMETRY["n"] = 0
                CURRENT_TELEMETRY["p"] = 0
                CURRENT_TELEMETRY["k"] = 0
                reading_captured = False
            
            update_dashboard()

    threading.Thread(target=telemetry_worker, daemon=True).start()

    def on_lever_changed(e):
        global lever_dropped, reading_captured
        if not bt_connected:
            log_activity("WARNING: Cannot deploy lever. Bluetooth link inactive.")
            chk_lever.value = False
            page.update()
            return

        lever_dropped = e.control.value
        if lever_dropped:
            reading_captured = False
            lbl_status.value = "PROBE DEPLOYED"
            lbl_status.color = "#f59e0b"
            status_badge.bgcolor = "#78350f"
            lbl_lever_indicator.value = "LEVER: DEPLOYED"
            lbl_lever_indicator.color = "#f59e0b"
            log_activity("ALERT: Probe mechanism lowered into regional soil.")
            send_bt_command("LEVER_DOWN\n")
        else:
            CURRENT_TELEMETRY["moisture"] = 0.0
            CURRENT_TELEMETRY["n"] = 0
            CURRENT_TELEMETRY["p"] = 0
            CURRENT_TELEMETRY["k"] = 0
            reading_captured = False
            
            lbl_status.value = "ACTIVE LINK" if bt_connected else "DISCONNECTED"
            lbl_status.color = "#34d399" if bt_connected else "#ef4444"
            status_badge.bgcolor = "#064e3b" if bt_connected else "#450a0a"
            lbl_lever_indicator.value = "LEVER: RETRACTED"
            lbl_lever_indicator.color = "#34d399"
            log_activity("Probe retracted. Telemetry cleared.")
            send_bt_command("LEVER_UP\n")
        update_dashboard()

    def handle_pan_update(e: ft.DragUpdateEvent):
        if lever_dropped or not bt_connected:
            return
        
        touch_x = max(0, min(80, e.local_position.x - 20))
        touch_y = max(0, min(80, e.local_position.y - 20))
        
        joystick_thumb.left = touch_x
        joystick_thumb.top = touch_y
        
        dx = touch_x - 40
        dy = touch_y - 40
        
        norm_x = round(dx / 40.0, 2)
        norm_y = round(-dy / 40.0, 2)
        
        y_dir = "FWD" if norm_y > 0.25 else ("REV" if norm_y < -0.25 else "")
        x_dir = "RIGHT" if norm_x > 0.25 else ("LEFT" if norm_x < -0.25 else "")
        
        if y_dir and x_dir:
            direction = f"{y_dir}-{x_dir}"
        elif y_dir:
            direction = y_dir
        elif x_dir:
            direction = x_dir
        else:
            direction = "Idle"
            
        lbl_joy_vector.value = f"Vectors: ({norm_x}, {norm_y}) [{direction}]"
        page.update()

    def handle_pan_end(e):
        if not lever_dropped and bt_connected:
            joystick_thumb.left = 40
            joystick_thumb.top = 40
            lbl_joy_vector.value = "Vectors: (0.0, 0.0) [Idle]"
            page.update()

    # --- Layout Sections ---
    header_section = ft.Container(
        content=ft.Row([
            ft.Column([
                ft.Text("AGRI-ROVER TERMINAL", size=13, weight=ft.FontWeight.BOLD, color="#f8fafc"),
                ft.Text("Autonomous Field Unit v2.4", size=9, color="#64748b")
            ], spacing=2),
            status_badge
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        bgcolor="#111827", padding=12, border_radius=10, border=ft.Border.all(width=1, color="#1f2937")
    )

    connection_section = ft.Container(
        content=ft.Column([
            txt_mac_address,
            ft.Container(
                content=ft.Text("Establish Bluetooth Link", size=11, weight=ft.FontWeight.BOLD, color="#ffffff"),
                on_click=connect_bluetooth,
                bgcolor="#0284c7",
                alignment=ft.Alignment.CENTER,
                border_radius=6,
                height=36,
                ink=True
            )
        ], spacing=8),
        bgcolor="#111827", padding=12, border_radius=10, border=ft.Border.all(width=1, color="#1f2937")
    )

    telemetry_card = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("SOIL TELEMETRY DATA", size=10, weight=ft.FontWeight.BOLD, color="#64748b"),
                ft.Text("RAIGARH FIELD ARRAY", size=9, color="#0ea5e9")
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(
                content=ft.Column([
                    ft.Text("VOLUMETRIC MOISTURE RATIO", size=8, weight=ft.FontWeight.BOLD, color="#64748b"),
                    lbl_moisture_val
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor="#1f2937", padding=10, border_radius=8, alignment=ft.Alignment.CENTER
            ),
            ft.Row([
                ft.Container(content=ft.Column([ft.Text("Nitrogen", size=8, color="#64748b"), n_val, ft.Text("mg/kg", size=8, color="#4b5563")], horizontal_alignment=ft.CrossAxisAlignment.CENTER), bgcolor="#1f2937", padding=8, border_radius=8, expand=True),
                ft.Container(content=ft.Column([ft.Text("Phosphorus", size=8, color="#64748b"), p_val, ft.Text("mg/kg", size=8, color="#4b5563")], horizontal_alignment=ft.CrossAxisAlignment.CENTER), bgcolor="#1f2937", padding=8, border_radius=8, expand=True),
                ft.Container(content=ft.Column([ft.Text("Potassium", size=8, color="#64748b"), k_val, ft.Text("mg/kg", size=8, color="#4b5563")], horizontal_alignment=ft.CrossAxisAlignment.CENTER), bgcolor="#1f2937", padding=8, border_radius=8, expand=True),
            ], spacing=6)
        ], spacing=8),
        bgcolor="#111827", padding=12, border_radius=10, border=ft.Border.all(width=1, color="#1f2937")
    )

    joystick_pad = ft.GestureDetector(
        on_pan_update=handle_pan_update,
        on_pan_end=handle_pan_end,
        content=ft.Container(
            width=120, height=120, bgcolor="#030712", border_radius=60,
            border=ft.Border.all(width=2, color="#374151"),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            content=ft.Stack([joystick_thumb], width=120, height=120)
        )
    )

    pad_layout = ft.Column([
        ft.Text("▲ FWD", size=8, weight=ft.FontWeight.BOLD, color="#4b5563"),
        ft.Row([
            ft.Text("◄ L", size=8, weight=ft.FontWeight.BOLD, color="#4b5563"),
            joystick_pad,
            ft.Text("R ►", size=8, weight=ft.FontWeight.BOLD, color="#4b5563"),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=8),
        ft.Text("▼ REV", size=8, weight=ft.FontWeight.BOLD, color="#4b5563")
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2)

    control_panel = ft.Container(
        content=ft.Column([
            ft.Text("DRIVE & SAMPLING CONTROL", size=10, weight=ft.FontWeight.BOLD, color="#64748b"),
            ft.Row([
                pad_layout,
                ft.Column([
                    lbl_joy_vector,
                    lbl_lever_indicator,
                    chk_lever
                ], spacing=8, alignment=ft.MainAxisAlignment.CENTER)
            ], alignment=ft.MainAxisAlignment.SPACE_AROUND)
        ], spacing=8),
        bgcolor="#111827", padding=12, border_radius=10, border=ft.Border.all(width=1, color="#1f2937")
    )

    feed_section = ft.Container(
        content=ft.Column([
            ft.Text("TELEMETRY LOG STREAM", size=10, weight=ft.FontWeight.BOLD, color="#64748b"),
            ft.Container(content=log_list, bgcolor="#030712", padding=8, border_radius=6, height=140, border=ft.Border.all(width=1, color="#1f2937"))
        ], spacing=6),
        bgcolor="#111827", padding=12, border_radius=10, border=ft.Border.all(width=1, color="#1f2937")
    )

    page.add(
        header_section,
        connection_section,
        telemetry_card,
        control_panel,
        feed_section
    )

if __name__ == "__main__":
    ft.run(main)
