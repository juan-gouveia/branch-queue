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
