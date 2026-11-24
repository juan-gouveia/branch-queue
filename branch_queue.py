"""Modelo de tickets y gestión de colas por servicio de una sucursal bancaria."""

from collections import deque
from dataclasses import dataclass
from datetime import datetime
import itertools

# Única fuente de verdad de los servicios: construye las colas y el menú de la CLI.
SERVICE_TYPES = ("deposito", "retiro", "gestion_cuenta")


class InvalidServiceError(ValueError):
    """El tipo de servicio no es uno de SERVICE_TYPES."""


class EmptyQueueError(LookupError):
    """No hay clientes esperando en la cola del servicio solicitado."""


@dataclass(frozen=True, slots=True)
class Ticket:
    """Ticket emitido a un cliente. Inmutable: un ticket emitido no cambia."""

    number: int
    client_name: str
    service_type: str
    issued_at: datetime


class BranchQueue:
    """Mantiene una cola FIFO independiente por servicio y un contador global de tickets."""

    def __init__(self):
        # Una deque por servicio: encolar y retirar por los extremos es O(1)
        # y no depende de cuántos clientes esperan en otros servicios.
        self._queues = {service: deque() for service in SERVICE_TYPES}
        # next() sobre itertools.count es atómico en CPython (GIL), a diferencia de += 1.
        self._counter = itertools.count(1)

    def _queue_for(self, service_type):
        """Devuelve la cola del servicio o lanza InvalidServiceError si no existe."""
        try:
            return self._queues[service_type]
        except KeyError:
            valid = ", ".join(SERVICE_TYPES)
            raise InvalidServiceError(
                f"Servicio '{service_type}' no válido. Opciones: {valid}."
            ) from None

    def issue_ticket(self, client_name, service_type):
        """Crea un ticket, lo encola en su servicio y lo devuelve."""
        # Validar antes de next(): un número ya extraído del contador no se puede devolver,
        # así que un servicio inválido no debe consumir numeración.
        queue = self._queue_for(service_type)
        ticket = Ticket(
            number=next(self._counter),
            client_name=client_name,
            service_type=service_type,
            issued_at=datetime.now(),
        )
        queue.append(ticket)
        return ticket

    def call_next(self, service_type):
        """Retira y devuelve el ticket más antiguo del servicio."""
        queue = self._queue_for(service_type)
        # popleft() directo en vez de comprobar antes si la cola está vacía: la retirada es
        # la única mutación, es atómica y ocurre antes de devolver el ticket, sin ventana
        # entre comprobar y retirar en la que otro agente pudiera llevarse al mismo cliente.
        try:
            return queue.popleft()
        except IndexError:
            raise EmptyQueueError(
                f"No hay clientes esperando para '{service_type}'."
            ) from None

    def peek_next(self, service_type):
        """Devuelve el siguiente ticket del servicio sin retirarlo."""
        queue = self._queue_for(service_type)
        try:
            return queue[0]
        except IndexError:
            raise EmptyQueueError(
                f"No hay clientes esperando para '{service_type}'."
            ) from None

    def list_waiting(self):
        """Devuelve {servicio: [tickets en orden de atención]} con copias de cada cola."""
        return {service: list(queue) for service, queue in self._queues.items()}

    def stats(self):
        """Devuelve el número de clientes en espera por servicio y la clave 'total'."""
        # len() de una deque es O(1): no recorre los tickets.
        counts = {service: len(queue) for service, queue in self._queues.items()}
        counts["total"] = sum(counts.values())
        return counts
