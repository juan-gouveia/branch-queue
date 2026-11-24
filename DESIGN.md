# Notas de diseño

## 1. Una cola por tipo de servicio

### El problema de una lista compartida

Con una sola lista ordenada por llegada, cuando un agente queda libre tiene que buscar el primer ticket **de su servicio**:

```
[R1, R2, R3, R4, D5]    ← el agente de depósitos busca un "deposito"
 ↑   ↑   ↑   ↑   ↑
 recorre 4 retiros antes de encontrar D5
```

Eso cuesta O(n), donde n es el número total de personas esperando, sumando **todos** los servicios. Además, retirar un elemento del medio de una lista obliga a desplazar los que vienen detrás, que es otro O(n). Es el mismo problema que describe la responsable de operaciones: el agente de depósitos se queda parado mientras recorre a los clientes de retiros.

### La estructura elegida

`BranchQueue` mantiene un diccionario con una `collections.deque` por servicio:

```python
self._queues = {"deposito": deque(), "retiro": deque(), "gestion_cuenta": deque()}
```

- **Llegada:** el ticket se añade al final de la cola de su servicio con `append`, que es O(1).
- **Llamar al siguiente:** se retira el primero de la cola del agente con `popleft`, que también es O(1). El primero de esa cola es siempre el que más tiempo lleva esperando para ese servicio, así que no hay que buscar nada.
- El coste de `call_next` **no depende** de cuántas personas esperan en otros servicios. Las colas no se tocan entre sí.

Se usa `deque` y no `list` porque `list.pop(0)` es O(n): desplaza todos los elementos. `deque.popleft()` es O(1).

### Coste de cada operación

| Operación | Coste | Motivo |
|---|---|---|
| `issue_ticket` | O(1) | Búsqueda en el diccionario + `append` |
| `call_next` | O(1) | Búsqueda en el diccionario + `popleft` |
| `peek_next` | O(1) | Búsqueda en el diccionario + `queue[0]` |
| `stats` | O(s) | `len()` de cada deque es O(1); s = 3 servicios. No recorre tickets |
| `list_waiting` | O(n) | Tiene que devolver todos los tickets: el recorrido es inevitable |

## 2. Dos agentes llaman a `call_next` a la vez

### El escenario

Dos agentes de depósitos quedan libres al mismo tiempo y en la cola queda **un solo** cliente, el ticket #7. Si el sistema primero *mira* quién es el siguiente y después lo retira, los dos agentes pueden ver al #7 antes de que ninguno lo retire:

```
Agente A: mira → #7         Agente B: mira → #7
Agente A: anuncia #7        Agente B: anuncia #7   ← mismo cliente llamado dos veces
Agente A: retira #7         Agente B: retira → cola vacía / error
```

Pasa lo mismo con "comprobar si la cola está vacía y después retirar": entre la comprobación y la retirada, otro agente puede llevarse el último ticket.

### Qué mutación debe ocurrir primero

**La retirada del ticket de la cola (`popleft`) debe ser la primera mutación de estado y debe ser atómica.** Solo después de retirarlo se devuelve, se anuncia o se registra. Así, quien retira el ticket es el único que lo tiene: el otro agente recibe el siguiente cliente o un aviso de cola vacía, nunca el mismo ticket.

`call_next` está escrito así:

```python
try:
    return queue.popleft()
except IndexError:
    raise EmptyQueueError(...)
```

No comprueba antes si la cola está vacía: intenta retirar y, si no hay nadie, informa. La retirada es la única operación sobre la cola y no hay ventana entre comprobar y retirar. En CPython, `deque.popleft()` es seguro entre hilos, como indica su documentación.

### El contador de tickets: segundo punto de carrera

La numeración global tiene el mismo riesgo. `self._counter += 1` son tres pasos (leer, sumar y escribir), y dos quioscos podrían leer el mismo valor y emitir dos tickets con el mismo número. El prototipo usa `next(itertools.count(1))`, que en CPython se ejecuta de una vez gracias al GIL. Es un detalle de implementación de CPython, no una garantía del lenguaje.

### Qué haría falta en una versión concurrente real

El prototipo se ejecuta en un solo hilo y **no implementa** concurrencia. Una versión para varios quioscos y agentes simultáneos necesitaría sincronización explícita:

- **Un `threading.Lock` por cola de servicio.** Los agentes del mismo servicio se turnan para retirar, pero un agente de depósitos no bloquea a uno de retiros.
- **Un lock para el contador** o para toda la emisión, de modo que asignar el número y encolar el ticket ocurran juntos y los números sigan el orden de llegada.

Si el sistema pasara a varios procesos o servidores, estos locks en memoria dejarían de bastar y la retirada atómica tendría que hacerla el almacén compartido (por ejemplo, una transacción en base de datos).

## 3. Otras decisiones

- **Validar antes de numerar.** `issue_ticket` comprueba el servicio antes de pedir el número al contador. Un número que ya salió de `itertools.count` no se puede devolver, así que un servicio inválido no debe consumir numeración.
- **Una única fuente de servicios.** `SERVICE_TYPES` construye las colas y el menú de la CLI. La validación consiste en buscar la cola en el diccionario (`_queue_for`).
- **Tickets inmutables.** `Ticket` es una `dataclass(frozen=True, slots=True)`: un ticket emitido no cambia, y `slots` reduce la memoria por instancia.
- **Errores con significado.** `InvalidServiceError` hereda de `ValueError` y `EmptyQueueError` de `LookupError`. `call_next` y `peek_next` lanzan la misma excepción con la cola vacía, así que la CLI tiene un solo caso que capturar.
- **Lógica y terminal separadas.** `branch_queue.py` no lee ni escribe en la consola. `cli.py` solo usa la interfaz pública de `BranchQueue` y recibe `input_fn` y `output_fn` como parámetros, lo que permite probar el menú sin consola.
