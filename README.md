# Gestor de colas para sucursal bancaria

Prototipo de terminal que organiza la espera en una sucursal de Banco Meridional. Cada cliente toma un ticket para uno de tres servicios (`deposito`, `retiro` o `gestion_cuenta`) y cada agente llama al siguiente cliente **de su servicio** al instante, sin recorrer a quienes esperan para otros servicios.

- Numeración de tickets global y secuencial desde 1, compartida por todos los servicios.
- Orden de llegada (FIFO) independiente dentro de cada servicio.
- Emitir, llamar al siguiente y ver el siguiente en tiempo constante.

## Requisitos

- Python 3.10 o superior.
- Sin dependencias externas: solo la biblioteca estándar.

## Uso

```bash
python cli.py
```

El menú se repite hasta elegir **Salir**:

```
=== Banco Meridional: gestor de colas ===
1) Emitir ticket
2) Llamar al siguiente
3) Ver siguiente (sin llamar)
4) Ver lista de espera
5) Ver estadísticas
6) Salir
```

El servicio se puede indicar por número (`1`, `2`, `3`) o por nombre. Las entradas inválidas y las colas vacías muestran un mensaje y el menú continúa. Ctrl+C y Ctrl+D salen sin error.

### Uso como biblioteca

```python
from branch_queue import BranchQueue

queue = BranchQueue()
queue.issue_ticket("Ana", "retiro")      # Ticket(number=1, ...)
queue.issue_ticket("Beto", "deposito")   # Ticket(number=2, ...)
queue.peek_next("retiro")                # Ana, sin retirarla
queue.call_next("retiro")                # Ana, retirada de la cola
queue.stats()                            # {'deposito': 1, 'retiro': 0, 'gestion_cuenta': 0, 'total': 1}
```

Un servicio inválido lanza `InvalidServiceError` y una cola vacía lanza `EmptyQueueError`.

## Pruebas

Desde la raíz del proyecto:

```bash
python -m unittest -v
```

## Estructura

| Archivo | Contenido |
|---|---|
| `branch_queue.py` | `Ticket`, `BranchQueue`, `SERVICE_TYPES` y las excepciones |
| `cli.py` | Menú de terminal |
| `test_branch_queue.py` | Pruebas `unittest` |
| `DESIGN.md` | Por qué una cola por servicio y cómo evitar llamar dos veces al mismo cliente |

## Diseño

Las decisiones de diseño, el coste de cada operación y el análisis de llamadas concurrentes están en [DESIGN.md](DESIGN.md).
