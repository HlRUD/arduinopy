from flask import Flask, jsonify, request, render_template_string
import serial
import serial.tools.list_ports
import threading
import time

app = Flask(__name__)

BAUDRATE = 9600
arduino = None
lock = threading.Lock()

HTML = r"""
<!DOCTYPE html>
<html lang="fa" dir="rtl">

<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>Arduino Control</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: #0b0b0f;
    color: white;
    font-family: Arial, sans-serif;
}

header {
    padding: 20px;
    background: #111118;
    border-bottom: 1px solid #292932;
}

h1 {
    margin: 0;
    font-size: 25px;
}

.container {
    max-width: 900px;
    margin: auto;
    padding: 15px;
}

.status {
    background: #15151d;
    padding: 15px;
    border-radius: 15px;
    margin-bottom: 15px;
}

.connected {
    color: #00e676;
}

.disconnected {
    color: #ff5252;
}

.all-off {
    width: 100%;
    padding: 16px;
    border: none;
    border-radius: 14px;
    background: #d50000;
    color: white;
    font-size: 18px;
    font-weight: bold;
    margin-bottom: 15px;
    cursor: pointer;
}

.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 12px;
}

.card {
    background: #15151d;
    border: 1px solid #292932;
    border-radius: 18px;
    padding: 16px;
}

.pin-title {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.pin {
    color: #888;
    font-size: 13px;
}

.name {
    font-size: 20px;
    font-weight: bold;
}

.rename {
    display: flex;
    gap: 5px;
    margin-top: 12px;
}

.rename input {
    flex: 1;
    background: #0b0b0f;
    color: white;
    border: 1px solid #333;
    border-radius: 10px;
    padding: 10px;
}

button {
    border: none;
    border-radius: 10px;
    padding: 10px 14px;
    cursor: pointer;
}

.save {
    background: #2979ff;
    color: white;
}

.toggle {
    width: 100%;
    margin-top: 12px;
    padding: 14px;
    font-size: 17px;
}

.on {
    background: #00c853;
    color: white;
}

.off {
    background: #424242;
    color: white;
}

.pwm {
    margin-top: 15px;
}

.pwm input {
    width: 100%;
}

.timer {
    display: flex;
    gap: 5px;
    margin-top: 12px;
}

.timer input {
    width: 80px;
    background: #0b0b0f;
    color: white;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 9px;
}

.log {
    margin-top: 20px;
    background: #111118;
    padding: 15px;
    border-radius: 15px;
}

.log-entry {
    color: #aaa;
    border-bottom: 1px solid #222;
    padding: 7px 0;
}

</style>
</head>

<body>

<header>
    <h1>⚡ Arduino Control</h1>
</header>

<div class="container">

    <div class="status">
        Arduino:
        <b id="connection">در حال بررسی...</b>
    </div>

    <button class="all-off" onclick="allOff()">
        خاموش کردن همه
    </button>

    <div class="grid" id="pins"></div>

    <div class="log">
        <h3>گزارش فعالیت</h3>
        <div id="logs"></div>
    </div>

</div>

<script>

const pins = [
    2,3,4,5,6,7,8,9,10,11,12,13
];

const pwmPins = [3,5,6,9,10,11];

let states = {};

let names = JSON.parse(
    localStorage.getItem("pinNames") || "{}"
);

pins.forEach(pin => {
    if (!names[pin]) {
        names[pin] = "پایه " + pin;
    }

    states[pin] = false;
});

localStorage.setItem(
    "pinNames",
    JSON.stringify(names)
);

function createPins() {

    const container = document.getElementById("pins");

    container.innerHTML = "";

    pins.forEach(pin => {

        const card = document.createElement("div");
        card.className = "card";

        const pwm = pwmPins.includes(pin);

        card.innerHTML = `

            <div class="pin-title">

                <div>
                    <div class="name" id="name-${pin}">
                        ${names[pin]}
                    </div>

                    <div class="pin">
                        D${pin}
                    </div>
                </div>

            </div>

            <div class="rename">

                <input
                    id="input-${pin}"
                    value="${names[pin]}"
                >

                <button
                    class="save"
                    onclick="renamePin(${pin})">
                    ذخیره
                </button>

            </div>

            <button
                id="button-${pin}"
                class="toggle off"
                onclick="togglePin(${pin})">

                روشن کردن

            </button>

            ${
                pwm
                ?
                `
                <div class="pwm">

                    <label>
                        شدت PWM:
                        <span id="pwmValue-${pin}">0</span>
                    </label>

                    <input
                        type="range"
                        min="0"
                        max="255"
                        value="0"
                        oninput="setPWM(${pin}, this.value)"
                    >

                </div>
                `
                :
                ""
            }

            <div class="timer">

                <input
                    id="timer-${pin}"
                    type="number"
                    min="1"
                    placeholder="ثانیه"
                >

                <button
                    class="save"
                    onclick="startTimer(${pin})">
                    تایمر خاموشی
                </button>

            </div>
        `;

        container.appendChild(card);
    });
}

function renamePin(pin) {

    const input = document.getElementById(
        "input-" + pin
    );

    names[pin] = input.value || ("پایه " + pin);

    localStorage.setItem(
        "pinNames",
        JSON.stringify(names)
    );

    document.getElementById(
        "name-" + pin
    ).textContent = names[pin];

    addLog(
        names[pin] + " → نام تغییر کرد"
    );
}

async function sendCommand(command) {

    try {

        const response = await fetch(
            "/command",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                    "application/json"
                },

                body: JSON.stringify({
                    command: command
                })
            }
        );

        return await response.json();

    } catch (error) {

        addLog("خطا در ارتباط با Python");

        return {
            success: false
        };
    }
}

async function togglePin(pin) {

    const newState = !states[pin];

    const command =
        newState
        ? "ON:" + pin
        : "OFF:" + pin;

    const result = await sendCommand(command);

    if (!result.success) return;

    states[pin] = newState;

    updateButton(pin);

    addLog(
        names[pin] +
        " → " +
        (newState ? "روشن" : "خاموش")
    );
}

function updateButton(pin) {

    const button =
        document.getElementById(
            "button-" + pin
        );

    if (states[pin]) {

        button.className =
            "toggle on";

        button.textContent =
            "خاموش کردن";

    } else {

        button.className =
            "toggle off";

        button.textContent =
            "روشن کردن";
    }
}

async function setPWM(pin, value) {

    document.getElementById(
        "pwmValue-" + pin
    ).textContent = value;

    await sendCommand(
        "PWM:" + pin + ":" + value
    );

    states[pin] = value > 0;

    updateButton(pin);
}

async function startTimer(pin) {

    const input =
        document.getElementById(
            "timer-" + pin
        );

    const seconds =
        parseInt(input.value);

    if (!seconds || seconds < 1) {
        alert("زمان معتبر وارد کن");
        return;
    }

    await sendCommand("ON:" + pin);

    states[pin] = true;
    updateButton(pin);

    addLog(
        names[pin] +
        " → تایمر " +
        seconds +
        " ثانیه"
    );

    setTimeout(async () => {

        await sendCommand(
            "OFF:" + pin
        );

        states[pin] = false;

        updateButton(pin);

        addLog(
            names[pin] +
            " → تایمر تمام شد"
        );

    }, seconds * 1000);
}

async function allOff() {

    const result =
        await sendCommand(
            "ALL:OFF"
        );

    if (!result.success) return;

    pins.forEach(pin => {

        states[pin] = false;

        updateButton(pin);
    });

    addLog("همه پایه‌ها → خاموش");
}

function addLog(text) {

    const logs =
        document.getElementById("logs");

    const entry =
        document.createElement("div");

    entry.className =
        "log-entry";

    const time =
        new Date().toLocaleTimeString();

    entry.textContent =
        time + "  " + text;

    logs.prepend(entry);
}

async function checkConnection() {

    try {

        const response =
            await fetch("/status");

        const data =
            await response.json();

        const element =
            document.getElementById(
                "connection"
            );

        if (data.connected) {

            element.textContent =
                "🟢 متصل";

            element.className =
                "connected";

        } else {

            element.textContent =
                "🔴 قطع";

            element.className =
                "disconnected";
        }

    } catch {

        document.getElementById(
            "connection"
        ).textContent =
            "🔴 Python قطع است";
    }
}

createPins();

checkConnection();

setInterval(
    checkConnection,
    3000
);

</script>

</body>
</html>
"""


def find_arduino():
    ports = serial.tools.list_ports.comports()

    for port in ports:
        description = (port.description or "").lower()
        manufacturer = (port.manufacturer or "").lower()

        if (
            "arduino" in description
            or "arduino" in manufacturer
            or "ch340" in description
            or "cp210" in description
        ):
            return port.device

    return None


def connect_arduino():

    global arduino

    port = find_arduino()

    if not port:
        print("Arduino پیدا نشد.")
        return False

    try:

        arduino = serial.Serial(
            port,
            BAUDRATE,
            timeout=1
        )

        time.sleep(2)

        print("Arduino connected:", port)

        return True

    except Exception as e:

        print("Arduino connection error:", e)

        arduino = None

        return False


def send_serial(command):

    global arduino

    with lock:

        try:

            if arduino is None or not arduino.is_open:

                if not connect_arduino():
                    return False

            arduino.write(
                (command + "\n").encode()
            )

            arduino.flush()

            print("SEND:", command)

            return True

        except Exception as e:

            print("Serial error:", e)

            try:
                arduino.close()
            except:
                pass

            arduino = None

            return False


@app.route("/")
def home():
    return render_template_string(HTML)


@app.route("/status")
def status():

    connected = (
        arduino is not None
        and arduino.is_open
    )

    return jsonify({
        "connected": connected
    })


@app.route("/command", methods=["POST"])
def command():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False
        })

    command = data.get("command", "")

    if not command:
        return jsonify({
            "success": False
        })

    success = send_serial(command)

    return jsonify({
        "success": success
    })


if __name__ == "__main__":

    connect_arduino()

    print()
    print("================================")
    print(" Arduino Web Control")
    print("================================")
    print("Open on this PC:")
    print("http://localhost:8080")
    print()
    print("For phone:")
    print("http://LAPTOP-IP:8080")
    print()

    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False
    )