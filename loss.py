import torch
import torch.nn.functional as F
import torch.nn as nn
from perceptual import PerceptualNet
from colors import ImageNetNormalize

class StyleLoss(nn.Module):
    def __init__(self):
        super(StyleLoss, self).__init__()
        self.style_layers = [
                'conv1_1', 'relu2_1', 'relu3_1', 'relu4_1', 'relu5_1']
        self.content_layers = ['conv3_2']
        self.normalize = ImageNetNormalize()
        self.net = PerceptualNet(self.style_layers + self.content_layers)


    def get_style_content_(self, img, detach):
        activations = self.net(self.normalize(img), detach=detach)
        style = {l: a
                for l, a in activations.items()
                if l in self.style_layers}

        content = {l: a
                for l, a in activations.items()
                if l in self.content_layers}

        return style, content


    def set_style(self, style_img, style_ratio, style_layers=None):
        self.ratio = style_ratio

        if style_layers is not None:
            self.style_layers = style_layers
            self.net.set_keep_layers(self.style_layers + self.content_layers)

        with torch.no_grad():
            activations = self.get_style_content_(style_img[None], detach=True)[0]

        grams = {layer_id: StyleLoss.gram(layer_data)
                 for layer_id, layer_data in activations.items()}

        self.style_grams = grams


    def set_content(self, content_img, content_layers=None):
        if content_layers is not None:
            self.content_layers = content_layers
            self.net.set_keep_layers(self.style_layers + self.content_layers)

        with torch.no_grad():
            acts = self.get_style_content_(content_img[None], detach=True)[1]
        self.photo_activations = acts


    @staticmethod
    def gram(m):
        b, c, h, w = m.shape
        m = m.view(b, c, h * w)
        m1 = m
        m2 = m.permute(0, 2, 1)
        g = torch.bmm(m1, m2) / (c * h * w)
        return g


    def forward(self, input_img):
        style_acts, content_acts = self.get_style_content_(input_img, detach=False)

        style_loss = 0
        for j in style_acts:
            this_loss = F.mse_loss(
                    StyleLoss.gram(style_acts[j]),
                    self.style_grams[j],
                    reduction='sum')

            style_loss += (1 / len(style_acts)) * this_loss

        content_loss = 0
        for j in content_acts:
            content_loss += F.mse_loss(
                    content_acts[j], self.photo_activations[j])

        return content_loss + self.ratio * style_loss