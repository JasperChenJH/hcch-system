import torch.nn as nn
class myNN(nn.Module):
    def __init__(self):
        super(myNN, self).__init__()
        self.fc1 = nn.Linear(784, 500)
        self.fc2 = nn.Linear(500, 10)
        self.dropout = nn.Dropout(p=0.2)
        self.softmax = nn.LogSoftmax(dim=1)
    def forward(self, x):
        x = x.view(x.shape[0], -1)
        x = self.dropout(x)
        x = self.fc1(x)