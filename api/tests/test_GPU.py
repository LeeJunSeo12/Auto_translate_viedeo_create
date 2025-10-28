import torch
print("torch:", torch.__version__)
print("cuda:", torch.version.cuda)
print("avail:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("name:", torch.cuda.get_device_name(0))
    print("cc:", torch.cuda.get_device_capability(0))