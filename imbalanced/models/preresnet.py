"""
    PreResNet model definition
    ported from https://github.com/bearpaw/pytorch-classification/blob/master/models/cifar/preresnet.py
"""

import torch.nn as nn
import torchvision.transforms as transforms
from torchvision.models import resnet18, resnet34
import math
import torch
from functools import partial

__all__ = ["PreResNet110", "PreResNet56", "PreResNet8", "PreResNet83", "PreResNet164", "ResNet18", "ResNet34"]


def conv3x3(in_planes, out_planes, stride=1):
    return nn.Conv2d(
        in_planes, out_planes, kernel_size=3, stride=stride, padding=1, bias=False
    )


class BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super(BasicBlock, self).__init__()
        self.bn1 = nn.BatchNorm2d(inplanes)
        self.relu = nn.ReLU(inplace=True)
        self.conv1 = conv3x3(inplanes, planes, stride)
        self.bn2 = nn.BatchNorm2d(planes)
        self.conv2 = conv3x3(planes, planes)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        residual = x

        out = self.bn1(x)
        out = self.relu(out)
        out = self.conv1(out)

        out = self.bn2(out)
        out = self.relu(out)
        out = self.conv2(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual

        return out


class Bottleneck(nn.Module):
    expansion = 4

    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super(Bottleneck, self).__init__()
        self.bn1 = nn.BatchNorm2d(inplanes)
        self.conv1 = nn.Conv2d(inplanes, planes, kernel_size=1, bias=False)
        self.bn2 = nn.BatchNorm2d(planes)
        self.conv2 = nn.Conv2d(
            planes, planes, kernel_size=3, stride=stride, padding=1, bias=False
        )
        self.bn3 = nn.BatchNorm2d(planes)
        self.conv3 = nn.Conv2d(planes, planes * 4, kernel_size=1, bias=False)
        self.relu = nn.ReLU(inplace=True)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        residual = x

        out = self.bn1(x)
        out = self.relu(out)
        out = self.conv1(out)

        out = self.bn2(out)
        out = self.relu(out)
        out = self.conv2(out)

        out = self.bn3(out)
        out = self.relu(out)
        out = self.conv3(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual

        return out


class PreResNet(nn.Module):
    def __init__(self, num_classes=10, depth=110):
        super(PreResNet, self).__init__()
        if depth >= 44:
            assert (depth - 2) % 9 == 0, "depth should be 9n+2"
            n = (depth - 2) // 9
            block = Bottleneck
        else:
            assert (depth - 2) % 6 == 0, "depth should be 6n+2"
            n = (depth - 2) // 6
            block = BasicBlock

        self.inplanes = 16
        self.conv1 = nn.Conv2d(3, 16, kernel_size=3, padding=1, bias=False)
        self.layer1 = self._make_layer(block, 16, n)
        self.layer2 = self._make_layer(block, 32, n, stride=2)
        self.layer3 = self._make_layer(block, 64, n, stride=2)
        self.bn = nn.BatchNorm2d(64 * block.expansion)
        self.relu = nn.ReLU(inplace=True)
        self.avgpool = nn.AvgPool2d(8)
        self.fc = nn.Linear(64 * block.expansion, num_classes)

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, math.sqrt(2.0 / n))
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()

    def _make_layer(self, block, planes, blocks, stride=1):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = nn.Sequential(
                nn.Conv2d(
                    self.inplanes,
                    planes * block.expansion,
                    kernel_size=1,
                    stride=stride,
                    bias=False,
                )
            )

        layers = list()
        layers.append(block(self.inplanes, planes, stride, downsample))
        self.inplanes = planes * block.expansion
        for i in range(1, blocks):
            layers.append(block(self.inplanes, planes))

        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.conv1(x)

        x = self.layer1(x)  # 32x32
        x = self.layer2(x)  # 16x16
        x = self.layer3(x)  # 8x8
        x = self.bn(x)
        x = self.relu(x)

        x = self.avgpool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)

        return x


class PreResNet164:
    base = PreResNet
    args = list()
    kwargs = {"depth": 164}
    transform_train = transforms.Compose(
        [
            transforms.Resize(32),
            transforms.RandomCrop(32, padding=4),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
        ]
    )
    transform_test = transforms.Compose(
        [
            transforms.Resize(32),
            transforms.ToTensor(),
            transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
        ]
    )


def get_base(num_classes, weights, size = 18):
    #print (f' num_classes {num_classes}, weights {weights}')
    if size ==18:
        model  =resnet18(weights = weights)
    elif size ==34:
        model = resnet34(weights=weights)
    model.fc = torch.nn.Linear(model.fc.in_features, num_classes)
    torch.nn.init.xavier_uniform_(model.fc.weight)
    return  model


class ResNet34:
    base = partial(get_base,size = 34)
    args = list()
    kwargs = {}
    if False:
        MEAN_CIFAR = [0.4914672374725342, 0.4822617471218109, 0.4467701315879822]
        STD_CIFAR = [0.2412, 0.2377, 0.2563]
        transform_train = transforms.Compose(
            [
                #transforms.Resize(32),
                transforms.RandomCrop(32, padding=4),
                transforms.RandomHorizontalFlip(0.5),
                transforms.ToTensor(),
                transforms.Normalize(MEAN_CIFAR, STD_CIFAR),
            ]
        )
        transform_test = transforms.Compose(
            [
                transforms.Resize(32),
                transforms.ToTensor(),
                transforms.Normalize(MEAN_CIFAR, STD_CIFAR),
            ]
        )
    else:
        # Data loading code
        mean = (0.4914, 0.4822, 0.4465)
        stdev = (0.2023, 0.1994, 0.2010)
        transform_test = transforms.Compose([
            # Resize step is required as we will use a ResNet model, which accepts at leats 224x224 images
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean, stdev)
        ])
        transform_train = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.AutoAugment(policy=transforms.AutoAugmentPolicy.CIFAR10),
            transforms.ToTensor(),
            transforms.Normalize(mean, stdev)
        ])


class ResNet18:
    base = get_base
    args = list()
    kwargs = {}
    MEAN_CIFAR = [0.4914672374725342, 0.4822617471218109, 0.4467701315879822]
    STD_CIFAR = [0.2412, 0.2377, 0.2563]
    transform_train = transforms.Compose(
        [
            transforms.Resize(32),
            transforms.RandomCrop(32, padding=4),
            transforms.RandomHorizontalFlip(0.5),
            transforms.ToTensor(),
            transforms.Normalize(MEAN_CIFAR, STD_CIFAR),
        ]
    )
    transform_test = transforms.Compose(
        [
            transforms.Resize(32),
            transforms.ToTensor(),
            transforms.Normalize(MEAN_CIFAR, STD_CIFAR),
        ]
    )






class PreResNet110:
    base = PreResNet
    args = list()
    kwargs = {"depth": 110}
    transform_train = transforms.Compose(
        [
            transforms.Resize(32),
            transforms.RandomCrop(32, padding=4),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
        ]
    )
    transform_test = transforms.Compose(
        [
            transforms.Resize(32),
            transforms.ToTensor(),
            transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
        ]
    )


class PreResNet83:
    base = PreResNet
    args = list()
    kwargs = {"depth": 83}
    transform_train = transforms.Compose(
        [
            transforms.Resize(32),
            transforms.RandomCrop(32, padding=4),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
        ]
    )
    transform_test = transforms.Compose(
        [
            transforms.Resize(32),
            transforms.ToTensor(),
            transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
        ]
    )


class PreResNet56:
    base = PreResNet
    args = list()
    kwargs = {"depth": 56}


    transform_train = transforms.Compose(
        [
            transforms.Resize(32),
            transforms.RandomCrop(32, padding=4),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
        ]
    )
    transform_test = transforms.Compose(
        [
            transforms.Resize(32),
            transforms.ToTensor(),
            transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
        ]
    )


class PreResNet8:
    base = PreResNet
    args = list()
    kwargs = {"depth": 8}
    transform_train = transforms.Compose(
        [
            transforms.Resize(32),
            transforms.RandomCrop(32, padding=4),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
        ]
    )
    transform_test = transforms.Compose(
        [
            transforms.Resize(32),
            transforms.ToTensor(),
            transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
        ]
    )
