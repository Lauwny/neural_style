import sys
import numpy as np
import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models as M
from torchvision import transforms
import functools
from PIL import Image
import requests
import torch.optim as O
import io
import argparse
from perceptual import StyleLoss
from colors import transfer_colors
from image import get_parameterized_img
import cv2


def npimg_to_tensor(np_img):
    return transforms.ToTensor()(np_img)


class ArtisticStyleOptimizer:
    def __init__(self, device="cpu"):
        self.loss = StyleLoss().to(device)
        self.device = device


    def build_ref_acts(self, content_img, style_img, style_ratio):
        self.loss.set_style(npimg_to_tensor(style_img).to(self.device), style_ratio)
        self.loss.set_content(npimg_to_tensor(content_img).to(self.device))


    def optimize_img(self, canvas):
        opt = O.LBFGS(canvas.parameters(), lr=0.3, history_size=10)

        for i in range(15):
            def make_loss():
                opt.zero_grad()
                input_img = canvas()
                loss = self.loss(input_img)
                loss.backward()
                return loss

            loss = opt.step(make_loss)
            if i % 10 == 0:
                print(i, loss.item())

        return transforms.ToPILImage()(canvas().cpu().detach()[0])

    def __call__(self, content_img, style_img, style_ratio):
        self.build_ref_acts(content_img, style_img, style_ratio)
        canvas = get_parameterized_img(
                3, content_img.height, content_img.width, backend='limpid').to(self.device)
        return self.optimize_img(canvas)


def go(args, stylizer):
    content = Image.open(args.content)
    content.thumbnail((args.size, args.size))

    style_img = Image.open(args.style)
    if args.scale != 1.0:
        new_style_size = (
                int(style_img.width * args.scale),
                int(style_img.height * args.scale)
        )
        style_img = style_img.resize(new_style_size, Image.BILINEAR)

    result = stylizer(content, style_img, args.ratio)

    if args.preserve_colors == 'on':
        result = transfer_colors(content, result)

    result.save(args.out)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            description="Implementation of Neural Artistic Style by Gatys")
    parser.add_argument('--content', required=True)
    parser.add_argument('--style', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--size', type=int)
    parser.add_argument('--scale', type=float, default=1)
    parser.add_argument('--ratio', default=1, type=float)
    parser.add_argument('--preserve_colors', default='off')
    parser.add_argument('--device', default='cuda')
    args = parser.parse_args(sys.argv[1:])

    stylizer = ArtisticStyleOptimizer(device=args.device)
    go(args, stylizer)

