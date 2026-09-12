from flask import Flask, render_template_string, request
import serial

app = Flask(__name__)

arduino = serial.Serial("COM3", 9600, timeout=1)

HTML = """
<!DOCTYPE html>
<html lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>Arduino Control</title>

    <style>
        body {
            background: #111;
            color: white;
            font-family: Arial;
            text-align: center;
            padding-top: 80px;
        }

        button {
            width: 220px;
            height: 80px;
            font-size: 28px;
            border: none;
            border-radius: 20px;
            cursor: pointer;
        }

        .on {
            background: #00c853;
            color: white;
        }

        .off {
            background: #d50000;
            color: white;
        }

        #status {
            margin-top: 30px;
            font-size: 24px;
        }
    </style>
</head>

<body>

    <h1>Arduino Pin 9</h1>

    <button id="btn" class="off" onclick="toggle()">
        روشن
    </button>

    <div id="status">وضعیت: خاموش</div>

    <script>
        let state = false;

        function toggle() {
            state = !state;

            fetch("/arduino/" + (state ? "on" : "off"))
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateButton();
                    }
                });
        }

        function updateButton() {
            const btn = document.getElementById("btn");
            const status = document.getElementById("status");

            if (state) {
                btn.textContent = "خاموش";
                btn.className = "on";
                status.textContent = "وضعیت: روشن";
            } else {
                btn.textContent = "روشن";
                btn.className = "off";
                status.textContent = "وضعیت: خاموش";
            }
        }
    </script>

</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)


@app.route("/arduino/<state>")
def arduino_control(state):

    if state == "on":
        arduino.write(b"1")
        return {"success": True}

    if state == "off":
        arduino.write(b"0")
        return {"success": True}

    return {"success": False}


app.run(host="0.0.0.0", port=8080)