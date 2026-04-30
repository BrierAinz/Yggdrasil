# Knowledge Base: PyTorch CIFAR-10 Best Practices

## Arquitecturas Recomendadas

### 1. ResNet-18 (Balance velocidad/precisiÃ³n)
- Accuracy objetivo: ~93-95%
- Epochs: 50-100
- Learning rate: 0.1 con decay
- Batch size: 128
- Data augmentation: RandomCrop, HorizontalFlip, Normalize

### 2. Wide ResNet-28-10 (MÃ¡xima precisiÃ³n)
- Accuracy objetivo: ~96%
- Epochs: 200
- Learning rate: 0.1 con cosine annealing
- Weight decay: 5e-4
- Dropout: 0.3

### 3. EfficientNet-B0 (Eficiencia)
- Accuracy objetivo: ~94%
- Epochs: 100
- AutoAugment recomendado

## Preprocesamiento EstÃ¡ndar
```python
transform_train = transforms.Compose([
    transforms.RandomCrop(32, padding=4),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
])

transform_test = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
])
```

## Optimizadores Recomendados
1. SGD con momentum=0.9 (estÃ¡ndar para CIFAR)
2. AdamW para entrenamiento mÃ¡s rÃ¡pido
3. LARS para batch sizes grandes

## Schedulers
1. MultiStepLR: milestones=[100, 150], gamma=0.1
2. CosineAnnealingLR: T_max=200
3. ReduceLROnPlateau: patience=10

## RegularizaciÃ³n
- Weight decay: 5e-4
- Label smoothing: 0.1
- Mixup/Cutmix (avanzado)

## Checkpoint Strategy
- Guardar best model basado en validation accuracy
- Early stopping: patience=20
- Guardar cada 50 epochs
