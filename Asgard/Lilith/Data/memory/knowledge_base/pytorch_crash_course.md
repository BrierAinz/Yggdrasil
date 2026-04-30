# GuÃ­a de PyTorch para Ainz

## Conceptos Clave que Ainz debe recordar:
- Un modelo es una clase que hereda de `nn.Module`.
- El forward pass es `model(inputs)`.
- La pÃ©rdida se calcula con `criterion(outputs, labels)`.
- `optimizer.zero_grad()` antes de `loss.backward()`.
- `optimizer.step()` despuÃ©s de `loss.backward()`.

## Flujo de Trabajo TÃ­pico de Entrenamiento:
1.  **Definir Modelo:** `class MyModel(nn.Module): ...`
2.  **Instanciar:** `model = MyModel().to(device)` (device = 'cuda' o 'cpu').
3.  **Definir Optimizador y PÃ©rdida:** `optimizer = torch.optim.Adam(model.parameters(), lr=0.001)`, `criterion = nn.CrossEntropyLoss()`.
4.  **Bucle de Entrenamiento (epoch):**
    ```python
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        for data, labels in train_loader:
            # Mover datos a device
            data, labels = data.to(device), labels.to(device)

            # Forward pass
            outputs = model(data)
            loss = criterion(outputs, labels)

            # Backward y optimizaciÃ³n
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            running_loss += loss.item()

        print(f"Epoch {epoch+1}, Loss: {running_loss/len(train_loader)}")
    ```

## Snippets RÃ¡pidos
- **Guardar Modelo:** `torch.save(model.state_dict(), "model.pth")`
- **Cargar Modelo:** `model.load_state_dict(torch.load("model.pth"))`
- **Inferencia:** `model.eval()` y `with torch.no_grad(): ...`
