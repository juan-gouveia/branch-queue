"""Interfaz de terminal para el gestor de colas de la sucursal.

Uso: python cli.py
"""

from branch_queue import (
    SERVICE_TYPES,
    BranchQueue,
    EmptyQueueError,
    InvalidServiceError,
)

MENU = """
=== Banco Meridional: gestor de colas ===
1) Emitir ticket
2) Llamar al siguiente
3) Ver siguiente (sin llamar)
4) Ver lista de espera
5) Ver estadísticas
6) Salir"""

EXIT_OPTION = "6"


def _format_ticket(ticket):
    return (
        f"#{ticket.number} {ticket.client_name} ({ticket.service_type}), "
        f"emitido a las {ticket.issued_at:%H:%M:%S}"
    )


def _ask_service(input_fn, output_fn):
    """Pide el servicio por número o por nombre.

    Una entrada que no sea un número válido se devuelve tal cual: la valida
    BranchQueue, que lanza InvalidServiceError con su propio mensaje.
    """
    for index, service in enumerate(SERVICE_TYPES, 1):
        output_fn(f"  {index}) {service}")
    choice = input_fn("Servicio (número o nombre): ").strip().lower()
    if choice.isdigit() and 1 <= int(choice) <= len(SERVICE_TYPES):
        return SERVICE_TYPES[int(choice) - 1]
    return choice


def _issue(queue, input_fn, output_fn):
    name = input_fn("Nombre del cliente: ").strip()
    if not name:
        output_fn("El nombre del cliente no puede estar vacío.")
        return
    ticket = queue.issue_ticket(name, _ask_service(input_fn, output_fn))
    output_fn(f"Ticket emitido: {_format_ticket(ticket)}")


def _call(queue, input_fn, output_fn):
    ticket = queue.call_next(_ask_service(input_fn, output_fn))
    output_fn(f"Llamando a: {_format_ticket(ticket)}")


def _peek(queue, input_fn, output_fn):
    ticket = queue.peek_next(_ask_service(input_fn, output_fn))
    output_fn(f"Siguiente en espera: {_format_ticket(ticket)}")


def _list(queue, input_fn, output_fn):
    for service, tickets in queue.list_waiting().items():
        output_fn(f"{service} ({len(tickets)}):")
        if not tickets:
            output_fn("  (sin clientes en espera)")
        for ticket in tickets:
            output_fn(f"  {_format_ticket(ticket)}")


def _stats(queue, input_fn, output_fn):
    for key, count in queue.stats().items():
        output_fn(f"  {key}: {count}")


ACTIONS = {"1": _issue, "2": _call, "3": _peek, "4": _list, "5": _stats}


def run_cli(queue=None, input_fn=input, output_fn=print):
    """Ejecuta el menú en bucle hasta que el usuario elige salir.

    input_fn y output_fn se pueden sustituir para probar el bucle sin consola.
    """
    if queue is None:
        queue = BranchQueue()
    try:
        while True:
            output_fn(MENU)
            choice = input_fn("Opción: ").strip()
            if choice == EXIT_OPTION:
                break
            action = ACTIONS.get(choice)
            if action is None:
                output_fn(f"Opción '{choice}' no válida. Elige un número del 1 al 6.")
                continue
            try:
                action(queue, input_fn, output_fn)
            except (InvalidServiceError, EmptyQueueError) as exc:
                output_fn(f"Error: {exc}")
    except (EOFError, KeyboardInterrupt):
        # Ctrl+D / Ctrl+C se tratan como «Salir», sin traceback.
        output_fn("")
    output_fn("Hasta luego.")


if __name__ == "__main__":
    run_cli()
