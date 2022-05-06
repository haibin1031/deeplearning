# -*- coding: utf-8 -*-
"""Domain-Adversarial-Training (DANN)

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1JO96Et-37GXtdBS0m6rXqEjd_mF3L4R3
"""

# Imports
import torch
import torch.nn as nn
from torchvision import transforms
from torchvision import datasets
from torch import optim
import math
import torch.nn.functional as F
from torch.autograd import Function
from sklearn.metrics import accuracy_score
import numpy as np
import numpy.testing as npt
import random
import os
from matplotlib import pyplot as plt
from digits import get_mnist
from digits import get_svhn

manual_seed = 0

random.seed(manual_seed)
np.random.seed(manual_seed)
torch.manual_seed(manual_seed)

if torch.cuda.is_available():
    torch.cuda.manual_seed_all(manual_seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    os.environ['PYTHONHASHSEED'] = '0'

getRGB = True
src_trX, src_trY, src_tsX, src_tsY = get_svhn(getRGB=getRGB)
#m,_,_,_ = src_trX.shape
#tr_idx = np.random.choice(m,min(m,TRAIN_SAMPLES_TO_USE))
#src_trX = src_trX[tr_idx,:,:,:]
#src_trY = src_trY[tr_idx]
#m,_,_,_ = src_tsX.shape
#ts_idx = np.random.choice(m,min(m,TEST_SAMPLES_TO_USE))
#src_tsX = src_tsX[ts_idx,:,:,:]
#src_tsY = src_tsY[ts_idx]
print('Src Train Min: Value- ',np.min(src_trX))
print('Src Train Max: Value- ',np.max(src_trX))
print('Src Test Min: Value- ',np.min(src_tsX))
print('Src Test Max: Value- ',np.max(src_tsX))
print('src_trX.shape: ', src_trX.shape)
print('src_trY.shape: ', src_trY.shape)
print('src_tsX.shape: ', src_tsX.shape)
print('src_tsY.shape: ', src_tsY.shape)

#Let's visualize few samples and their labels from the train and test dataset.
if getRGB:
    # For RGB svhn
    visx_tr = src_trX[:50,:,:,:].reshape(5,10,3,32,32).transpose(0,3,1,4,2).reshape(32*5,-1,3)
    visx_ts = src_tsX[:50,:,:,:].reshape(5,10,3,32,32).transpose(0,3,1,4,2).reshape(32*5,-1,3)
    visx = np.concatenate((visx_tr,visx_ts), axis=0)
    visx = (visx+1)/2. #scaling back to [0-1]
else:
    # For grayscale svhn
    visx_tr = src_trX[:50,:,:,:].squeeze().reshape(5,10,32,32).transpose(0,2,1,3).reshape(32*5,-1)
    visx_ts = src_tsX[:50,:,:,:].squeeze().reshape(5,10,32,32).transpose(0,2,1,3).reshape(32*5,-1)
    visx = np.concatenate((visx_tr,visx_ts), axis=0)

visy = np.concatenate((src_trY[:50],src_tsY[:50])).reshape(10,-1)
print('labels')
print(visy)
plt.figure(figsize = (8,8))
plt.axis('off')
if getRGB:
    plt.imshow(visx)
else:
    plt.imshow(visx,cmap='gray')

#convert to torch tensor
src_trX = torch.tensor(src_trX)
src_trY = torch.tensor(src_trY)
src_tsX = torch.tensor(src_tsX)
src_tsY = torch.tensor(src_tsY)

getRGB = True
setSizeTo32 = False
size = 32 if setSizeTo32 else 28
tgt_trX, tgt_trY, tgt_tsX, tgt_tsY = get_mnist(getRGB=getRGB, setSizeTo32=setSizeTo32)
print('Tgt Train Min: Value- ',np.min(tgt_trX))
print('Tgt Train Max: Value- ',np.max(tgt_trX))
print('Tgt Test Min: Value- ',np.min(tgt_tsX))
print('Tgt Test Max: Value- ',np.max(tgt_tsX))
print('tgt_trX.shape: ', tgt_trX.shape)
print('tgt_trY.shape: ', tgt_trY.shape)
print('tgt_tsX.shape: ', tgt_tsX.shape)
print('tgt_tsY.shape: ', tgt_tsY.shape)

if getRGB:
    # For colorRGB svhn
    visx_tr = tgt_trX[:50,:,:,:].reshape(5,10,3,size,size).transpose(0,3,1,4,2).reshape(size*5,-1,3)
    visx_ts = tgt_tsX[:50,:,:,:].reshape(5,10,3,size,size).transpose(0,3,1,4,2).reshape(size*5,-1,3)
    visx = np.concatenate((visx_tr,visx_ts), axis=0)
    visx = (visx+1)/2. #scaling back to [0-1]
else:
    # For grayscale svhn
    visx_tr = tgt_trX[:50,:,:,:].squeeze().reshape(5,10,size,size).transpose(0,2,1,3).reshape(size*5,-1)
    visx_ts = tgt_tsX[:50,:,:,:].squeeze().reshape(5,10,size,size).transpose(0,2,1,3).reshape(size*5,-1)
    visx = np.concatenate((visx_tr,visx_ts), axis=0)

visy = np.concatenate((tgt_trY[:50],tgt_tsY[:50])).reshape(10,-1)
print('labels')
print(visy)
plt.figure(figsize = (8,8))
plt.axis('off')
if getRGB:
    plt.imshow(visx)
else:
    plt.imshow(visx,cmap='gray')

#convert to torch tensor
tgt_trX = torch.tensor(tgt_trX)
tgt_trY = torch.tensor(tgt_trY)
tgt_tsX = torch.tensor(tgt_tsX)
tgt_tsY = torch.tensor(tgt_tsY)

class FeatureExtractor(nn.Module):
    def __init__(self):
        super(FeatureExtractor, self).__init__()
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, stride=1, padding=1)
        self.relu1 = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(32, 32, kernel_size=3, stride=1, padding=1)
        self.relu2 = nn.ReLU(inplace=True)
        self.maxpool1 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.bn1 = nn.BatchNorm2d(32)
        self.conv3 = nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1)
        self.relu3 = nn.ReLU(inplace=True)
        self.conv4 = nn.Conv2d(64, 64, kernel_size=3, stride=1, padding=1)
        self.relu4 = nn.ReLU(inplace=True)
        self.maxpool2 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.bn2 = nn.BatchNorm2d(64)
        self.conv5 = nn.Conv2d(64, 128, kernel_size=3, stride=1, padding=1)
        self.relu5 = nn.ReLU(inplace=True)
        self.conv6 = nn.Conv2d(128, 128, kernel_size=3, stride=1, padding=1)
        self.relu6 = nn.ReLU(inplace=True)
        self.Avgpool = nn.AdaptiveAvgPool2d(1)
        self.fc1 = nn.Linear(in_features=128*1*1,out_features=128)
        self.flatten = nn.Flatten()
        self.relu7 = nn.ReLU(inplace=True)
        self.bn3 = nn.BatchNorm1d(128)
        
        for m in self.modules():
            if isinstance(m, nn.Conv2d) or isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight)

    def forward(self, x):
        
        x = self.conv1(x)
        x = self.relu1(x)
        x = self.conv2(x)
        x = self.relu2(x)
        x = self.maxpool1(x)
        x = self.bn1(x)
        x = self.conv3(x)
        x = self.relu3(x)
        x = self.conv4(x)
        x = self.relu4(x)
        x = self.maxpool2(x)
        x = self.bn2(x)
        x = self.conv5(x)
        x = self.relu5(x)
        x = self.Avgpool(x)
        N,C,H,W = x.size()
        x=x.view(N,C*H*W)
        x = self.fc1(x)
        x = self.relu7(x)
        x = self.bn3(x)
        return x


class LabelClassifier(nn.Module):
    def __init__(self):
        super(LabelClassifier, self).__init__()
        self.fc1 = nn.Linear(128, 64)
        self.relu1 = nn.ReLU(inplace=True)
        self.bn1 = nn.BatchNorm1d(64)
        self.fc2 = nn.Linear(64, 10)
        for m in self.modules():
            if isinstance(m, nn.Conv2d) or isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0.0, 0.02)

    def forward(self, x):
        x = self.fc1(x)
        x = self.relu1(x)
        x = self.bn1(x)
        x = self.fc2 (x)
        return x

class GradReverse(Function):
    @staticmethod
    def forward(ctx, x, lamda):
        ctx.lamda = lamda
        return x.view_as(x)

    @staticmethod
    def backward(ctx, grad_output):
        output = (grad_output.neg() * ctx.lamda)
        return output, None

class DomainClassifier(nn.Module):
    def __init__(self):
        super(DomainClassifier, self).__init__()
        self.fc1 = nn.Linear(128, 64)
        self.relu1 = nn.ReLU(inplace=True)
        self.bn1 = nn.BatchNorm1d(64)
        self.fc2 = nn.Linear(64, 64)
        self.relu2 = nn.ReLU(inplace=True)
        self.bn2 = nn.BatchNorm1d(64)
        self.fc3 = nn.Linear(64, 1)
        for m in self.modules():
            if isinstance(m, nn.Conv2d) or isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0.0, 0.02)

    def forward(self, x, lam=0.0):
        x = GradReverse.apply(x, lam)
        x = self.fc1(x)
        x = self.relu1(x)
        x = self.bn1(x)
        x = self.fc2(x)
        x = self.relu2(x)
        x = self.bn2(x)
        x = self.fc3(x)
        return torch.sigmoid(x)

f_t = FeatureExtractor()
c_t = LabelClassifier()
d_t = DomainClassifier()
x_t = torch.Tensor(np.random.randn(5,3,32,32))
x_f_t = f_t(x_t)
npt.assert_array_equal(x_f_t.shape, (5,128))
x_f_t = torch.Tensor(np.random.randn(5,128))
x_c_t = c_t(x_f_t)
npt.assert_array_equal(x_c_t.shape, (5,10))
x_d_t = d_t(x_f_t)
npt.assert_array_equal(x_d_t.shape, (5,1))
assert torch.all(x_d_t>0) and torch.all(x_d_t<= 1.)

BATCH_SIZE = 64
LR = 1e-2 # learning rate
LR_decay_rate = 0.999 
TOTAL_EPOCHS = 5 
LOG_PRINT_STEP = 200 

ftr_extr = FeatureExtractor()
lbl_clsfr = LabelClassifier()
dom_clsfr = DomainClassifier()

if is_cuda:
    ftr_extr = ftr_extr.cuda()
    lbl_clsfr = lbl_clsfr.cuda()
    dom_clsfr = dom_clsfr.cuda()

opt = optim.Adam(list(ftr_extr.parameters()) + list(lbl_clsfr.parameters()), betas=(0.9, 0.999), lr=LR, weight_decay=0.0005)
my_lr_scheduler = torch.optim.lr_scheduler.ExponentialLR(optimizer=opt, gamma=LR_decay_rate)

ce_criterion = nn.CrossEntropyLoss()

print("-----------------------------------------FeatrureExtractor---------------------------------------")
print(ftr_extr)
print("\n------------------------------------------LabelClassifier------------------------------------------")
print(lbl_clsfr)
print("\n------------------------------------------CrossEntropyLoss------------------------------------------")
print(ce_criterion)
print("\n------------------------------------------DomainClassifier------------------------------------------")
print(dom_clsfr)

# Testcases
assert isinstance(ftr_extr, FeatureExtractor)
assert isinstance(lbl_clsfr, LabelClassifier)
assert isinstance(dom_clsfr, DomainClassifier)
assert isinstance(ce_criterion, nn.CrossEntropyLoss)

def calc_clf_logits(x):
    feature = ftr_extr(x)
    logits = lbl_clsfr(feature)
    return logits

x_t = torch.Tensor(np.random.randn(5,3,32,32))
if is_cuda:
    x_t = x_t.cuda()
npt.assert_array_equal(calc_clf_logits(x_t).shape, (5,10))

def src_clf_loss(img, Y):
    clf_loss = ce_criterion(calc_clf_logits(img), Y)
    return clf_loss

x_t = torch.Tensor(np.random.randn(5,3,32,32))
x_t.requires_grad = True
label_t = torch.empty(5, dtype=torch.long).random_(10)
if is_cuda:
    x_t = x_t.cuda()
    label_t = label_t.cuda()
out_t = src_clf_loss(x_t, label_t)
npt.assert_array_equal(out_t.shape, (1))

def evaluate_model(X, Y):
    ftr_extr.eval()
    lbl_clsfr.eval()
    actual = []
    pred = []
    
    m = X.shape[0]
    for ii in range((m - 1) // BATCH_SIZE + 1):
        img = X[ii*BATCH_SIZE : (ii+1)*BATCH_SIZE, :]
        label = Y[ii*BATCH_SIZE : (ii+1)*BATCH_SIZE]
        if is_cuda:
            img = img.cuda()
        logits = calc_clf_logits(img)
        _, predicted = torch.max(logits.data, 1)
        actual += label.tolist()
        pred += predicted.tolist()
    acc = accuracy_score(y_true=actual, y_pred=pred) * 100
    return acc

# Commented out IPython magic to ensure Python compatibility.
print("Iterations per epoch: %d"%(src_trX.shape[0]//BATCH_SIZE))
lbl_clsfr.train()
ftr_extr.train()
m = src_trX.shape[0]
for epoch in range(TOTAL_EPOCHS):
    for ii in range((m - 1) // BATCH_SIZE + 1):
        s_img = src_trX[ii*BATCH_SIZE : (ii+1)*BATCH_SIZE, :]
        s_labels = src_trY[ii*BATCH_SIZE : (ii+1)*BATCH_SIZE]
        
        if is_cuda:
            s_img, s_labels = s_img.cuda(), s_labels.cuda()
        
        clf_loss = src_clf_loss(s_img, s_labels)
        loss = clf_loss
        
        opt.zero_grad()
        loss.backward()
        opt.step()
        
        my_lr_scheduler.step()
                
        if ii % LOG_PRINT_STEP == 0:
            print("Epoch: %d/%d, iter: %4d, clf_err: %.4f, clf_LR: %.3E" \
#                   %(epoch+1, TOTAL_EPOCHS, ii, clf_loss, opt.param_groups[0]['lr']))

manual_seed = 0

random.seed(manual_seed)
np.random.seed(manual_seed)
torch.manual_seed(manual_seed)

if torch.cuda.is_available():
    torch.cuda.manual_seed_all(manual_seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    os.environ['PYTHONHASHSEED'] = '0'
    
############################################################################### 
LR = 1e-2
LR_decay_rate = 0.999
disc_LR = 1e-4
disc_LR_decay_rate = 0.999
TOTAL_EPOCHS = 5
LOG_PRINT_STEP = 200
ftr_extr = FeatureExtractor()
lbl_clsfr = LabelClassifier()
dom_clsfr = DomainClassifier()
if is_cuda:
    ftr_extr = ftr_extr.cuda()
    lbl_clsfr = lbl_clsfr.cuda()
    dom_clsfr = dom_clsfr.cuda()

opt = optim.Adam(list(ftr_extr.parameters()) + list(lbl_clsfr.parameters()), lr=LR, betas=[0.9, 0.999], weight_decay=0.0005)
my_lr_scheduler = torch.optim.lr_scheduler.ExponentialLR(optimizer=opt, gamma=LR_decay_rate)
optD = optim.Adam(dom_clsfr.parameters(), lr=disc_LR, betas=(0.9, 0.999), weight_decay=0.0005)
ce_criterion = nn.CrossEntropyLoss()
bce_criterion = nn.BCELoss()

def adjust_lambda(itr, epoch, no_itrs_per_epoch, n_epochs):
    num_p=itr+epoch*no_itrs_per_epoch
    denom_p=n_epochs*no_itrs_per_epoch
    p=num_p/denom_p
    gamma=10
    lam=(2/(1+math.exp(-gamma*p)))-1
    return lam

#Test
i = 1
epoch = 4
min_len = 100
nepochs = 10
lam = adjust_lambda(i, epoch, min_len, nepochs)
npt.assert_almost_equal(lam, 0.9643791367189494,decimal=5)

def domain_clf_loss(s_img, t_img, lam):
    GTL_src = torch.ones(s_img.size(0), 1)
    GTL_tgt = torch.zeros(t_img.size(0), 1)
    Labels = torch.cat((GTL_src, GTL_tgt),0)
    if is_cuda:
        Labels = Labels.cuda()
    ftr_extr_s_img=ftr_extr(s_img)
    ftr_extr_t_img=ftr_extr(t_img)
    imgs = torch.cat((ftr_extr_s_img, ftr_extr_t_img),0)
    if is_cuda:
        imgs = imgs.cuda()
    logits=dom_clsfr(imgs,lam)
    dom_loss=bce_criterion(logits,Labels)
    
    return dom_loss

x_t = torch.Tensor(np.random.randn(5,3,32,32))
x_t.requires_grad = True
label_t = torch.empty(5, dtype=torch.long).random_(10)
if is_cuda:
    x_t = x_t.cuda()
    label_t = label_t.cuda()
out_t = src_clf_loss(x_t, label_t)
npt.assert_array_equal(out_t.shape, (1))

# Commented out IPython magic to ensure Python compatibility.
#DANN
max_len = max(src_trX.shape[0], tgt_trX.shape[0])
print("Iterations per epoch: %d"%(max_len//BATCH_SIZE))
lbl_clsfr.train()
ftr_extr.train()
dom_clsfr.train()

src_bigger = False
src_idx = range((src_trX.shape[0] - 1) // BATCH_SIZE + 1)
tgt_idx = range((tgt_trX.shape[0] - 1) // BATCH_SIZE + 1)
if src_trX.shape[0] > tgt_trX.shape[0]:
    tgt_idx = np.resize(tgt_idx, src_trX.shape[0])
    src_bigger = True
else:
    src_idx = np.resize(src_idx, tgt_trX.shape[0])
    
for epoch in range(TOTAL_EPOCHS):
    for ii, jj in zip(src_idx, tgt_idx):
        s_img = src_trX[ii*BATCH_SIZE : (ii+1)*BATCH_SIZE, :]
        s_labels = src_trY[ii*BATCH_SIZE : (ii+1)*BATCH_SIZE]
        t_img = tgt_trX[jj*BATCH_SIZE : (jj+1)*BATCH_SIZE, :]
        t_labels = tgt_trY[jj*BATCH_SIZE : (jj+1)*BATCH_SIZE]
        
        if src_bigger:
            lam = adjust_lambda(ii, epoch, max_len//BATCH_SIZE, TOTAL_EPOCHS)
        else:
            lam = adjust_lambda(jj, epoch, max_len//BATCH_SIZE, TOTAL_EPOCHS)
            
        if is_cuda:
            s_img, s_labels, t_img, t_labels = s_img.cuda(), s_labels.cuda(), t_img.cuda(), t_labels.cuda()
        
        clf_loss = src_clf_loss(s_img, s_labels)
        
        dom_loss = domain_clf_loss(s_img, t_img, lam)
                  
        loss = clf_loss + dom_loss
        
        opt.zero_grad()
        optD.zero_grad()
        loss.backward()
        opt.step()
        optD.step()
        my_lr_scheduler.step()
        #my_lr_scheduler_D.step()
        
        if src_bigger:
            if ii % LOG_PRINT_STEP == 0:
                print("Epoch: %d/%d, iter: %4d, lambda: %.2f, clf_loss: %.4f, clf_LR: %.3E, dom_loss: %.4f, dom_LR: %.3E"\
#                       %(epoch+1, TOTAL_EPOCHS, ii, lam, clf_loss, opt.param_groups[0]['lr'], dom_loss, optD.param_groups[0]['lr']))
        else:
            if jj % LOG_PRINT_STEP == 0:
                print("Epoch: %d/%d, iter: %4d, lambda: %.2f, clf_err: %.4f, clf_LR: %.3E, disc_err: %.4f, dom_LR: %.3E"\
#                       %(epoch+1, TOTAL_EPOCHS, jj, lam, clf_loss, opt.param_groups[0]['lr'], dom_loss, optD.param_groups[0]['lr']))

# Commented out IPython magic to ensure Python compatibility.
src_train_acc2 = evaluate_model(src_trX, src_trY)
src_test_acc2 = evaluate_model(src_tsX, src_tsY)
tgt_train_acc2 = evaluate_model(tgt_trX, tgt_trY)
tgt_test_acc2 = evaluate_model(tgt_tsX, tgt_tsY)
print("With Domain Adversarial Training:\nSource train acc: %.2f\nSource test acc: %.2f\nTarget train acc: %.2f\nTarget test acc: %.2f" \
#       %(src_train_acc2, src_test_acc2, tgt_train_acc2, tgt_test_acc2))