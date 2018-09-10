from flask import Flask, request
import requests
import style
from torchvision import models as M
import base64
import io
from PIL import Image
import numpy as np

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/tmp/'

m = M.vgg19(pretrained=True).cuda().eval()
m = style.WithSavedActivations(m.features)


def wget(url, scale=None):
    r = requests.get(url)
    print(r.status_code)
    with io.BytesIO(r.content) as f:
        return open_img(f, scale)


def open_img(path, size=None):
    img = Image.open(path)
    if size is not None:
        img.thumbnail((size, size))
    return np.array(img)


def img_to_data_url(img):
    with io.BytesIO() as f:
        img = Image.fromarray(img, 'RGB')
        img.save(f, 'jpeg')
        f.seek(0)
        return 'data:image/jpg;base64,' + base64.b64encode(f.read()).decode()


@app.route('/go', methods=['GET', 'POST'])
def go():
    args = request.args

    content_scale = int(args['size'])
    style_scale = content_scale

    if args['content'].startswith('http'):
        content = wget(args['content'], content_scale)
    else:
        content = open_img(args['content'], content_scale)

    if args['style'].startswith('http'):
        style_img = wget(args['style'], style_scale)
    else:
        style_img = open_img(args['style'], style_scale)

    print(args)
    result = style.artistic_style(content, style_img, m,
            float(args.get('ratio', '1e1')))
    return '<img src="' + img_to_data_url(result) +'" />'


@app.route('/', methods=['GET'])
def index():
    return """
<!doctype html>
<html>
    <body>
        <h1>Neural Style</h1>
        <form id="upload" action="/go" method="GET">
            <input
                type="text"
                name="content"
                placeholder="content URL"
                required/>
            <input
                type="text"
                name="style"
                placeholder="style URL"
                required/>
            <input
                type="number"
                name="ratio"
                placeholder="Loss ratio"
                value="10"/>
            <select name="size">
                <option value="128">128</option>
                <option value="256">256</option>
                <option value="512">512</option>
                <option value="720">720</option>
                <option value="1024">1024</option>
            </select>
            <input type="submit"/>
        </form>
    </body>
    <script>
window.upload.onsubmit = (e) => {
};
    </script>
</html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
