"""Pruebas de BranchQueue y de la CLI. Ejecutar con: python -m unittest"""

from datetime import datetime
import unittest

from branch_queue import (
    SERVICE_TYPES,
    BranchQueue,
    EmptyQueueError,
    InvalidServiceError,
)
from cli import run_cli


class GlobalNumberingTest(unittest.TestCase):
    def test_numbers_are_global_and_consecutive_across_services(self):
        queue = BranchQueue()
        requests = [
            ("Ana", "retiro"),
            ("Beto", "deposito"),
            ("Cris", "gestion_cuenta"),
            ("Dani", "retiro"),
            ("Eva", "deposito"),
        ]
        tickets = [queue.issue_ticket(name, service) for name, service in requests]

        self.assertEqual([t.number for t in tickets], [1, 2, 3, 4, 5])
        for ticket, (name, service) in zip(tickets, requests):
            self.assertEqual(ticket.client_name, name)
            self.assertEqual(ticket.service_type, service)
            self.assertIsInstance(ticket.issued_at, datetime)
        issued = [t.issued_at for t in tickets]
        self.assertEqual(issued, sorted(issued))


class FifoAndIndependenceTest(unittest.TestCase):
    def test_each_service_is_fifo_and_independent(self):
        queue = BranchQueue()
        for name, service in [
            ("Ana", "retiro"),
            ("Beto", "deposito"),
            ("Cris", "retiro"),
            ("Dani", "deposito"),
            ("Eva", "retiro"),
        ]:
            queue.issue_ticket(name, service)
        deposits_before = queue.list_waiting()["deposito"]

        called = [queue.call_next("retiro").client_name for _ in range(3)]

        self.assertEqual(called, ["Ana", "Cris", "Eva"])
        self.assertEqual(queue.list_waiting()["deposito"], deposits_before)
        self.assertEqual(queue.call_next("deposito").client_name, "Beto")
        self.assertEqual(queue.call_next("deposito").client_name, "Dani")


class EmptyQueueTest(unittest.TestCase):
    def test_peek_does_not_remove(self):
        queue = BranchQueue()
        ticket = queue.issue_ticket("Ana", "retiro")

        self.assertIs(queue.peek_next("retiro"), ticket)
        self.assertIs(queue.peek_next("retiro"), ticket)
        self.assertEqual(queue.stats()["retiro"], 1)
        self.assertIs(queue.call_next("retiro"), ticket)

    def test_call_and_peek_on_empty_queue_raise_empty_queue_error(self):
        queue = BranchQueue()
        for service in SERVICE_TYPES:
            with self.assertRaisesRegex(EmptyQueueError, service):
                queue.call_next(service)
            with self.assertRaisesRegex(EmptyQueueError, service):
                queue.peek_next(service)


class InvalidServiceTest(unittest.TestCase):
    def test_invalid_service_is_rejected_without_changing_state(self):
        queue = BranchQueue()
        queue.issue_ticket("Ana", "retiro")
        waiting_before = queue.list_waiting()

        for operation, args in [
            (queue.issue_ticket, ("Beto", "prestamo")),
            (queue.call_next, ("prestamo",)),
            (queue.peek_next, ("prestamo",)),
        ]:
            with self.subTest(operation=operation.__name__):
                with self.assertRaisesRegex(InvalidServiceError, "prestamo"):
                    operation(*args)

        self.assertEqual(queue.list_waiting(), waiting_before)
        # El rechazo no consumió número: el siguiente ticket es el 2.
        self.assertEqual(queue.issue_ticket("Cris", "deposito").number, 2)


class ListingAndStatsTest(unittest.TestCase):
    def test_empty_branch_includes_every_service(self):
        queue = BranchQueue()

        self.assertEqual(queue.list_waiting(), {s: [] for s in SERVICE_TYPES})
        self.assertEqual(queue.stats(), {**{s: 0 for s in SERVICE_TYPES}, "total": 0})

    def test_listing_and_stats_follow_issue_and_call(self):
        queue = BranchQueue()
        ana = queue.issue_ticket("Ana", "retiro")
        beto = queue.issue_ticket("Beto", "deposito")
        cris = queue.issue_ticket("Cris", "retiro")

        self.assertEqual(
            queue.list_waiting(),
            {"deposito": [beto], "retiro": [ana, cris], "gestion_cuenta": []},
        )
        self.assertEqual(
            queue.stats(),
            {"deposito": 1, "retiro": 2, "gestion_cuenta": 0, "total": 3},
        )

        queue.call_next("retiro")

        self.assertEqual(queue.list_waiting()["retiro"], [cris])
        self.assertEqual(
            queue.stats(),
            {"deposito": 1, "retiro": 1, "gestion_cuenta": 0, "total": 2},
        )

        queue.list_waiting()["retiro"].clear()
        self.assertEqual(queue.stats()["retiro"], 1)


def scripted_input(*answers):
    """input_fn que responde en orden y lanza EOFError al agotarse, como Ctrl+D."""
    remaining = iter(answers)

    def input_fn(prompt=""):
        try:
            return next(remaining)
        except StopIteration:
            raise EOFError from None

    return input_fn


class CliTest(unittest.TestCase):
    def run_session(self, *answers, queue=None):
        queue = queue if queue is not None else BranchQueue()
        output = []
        run_cli(queue, input_fn=scripted_input(*answers), output_fn=output.append)
        return queue, "\n".join(output)

    def test_invalid_inputs_show_messages_and_loop_continues(self):
        queue, output = self.run_session(
            "9",                    # opción inválida
            "1", "   ",             # nombre vacío
            "1", "Ana", "prestamo",  # servicio inválido
            "2", "3",               # llamar en cola vacía (gestion_cuenta)
            "3", "1",               # ver siguiente en cola vacía (deposito)
            "1", "Beto", "Retiro",  # emisión válida, nombre de servicio
            "6",
        )

        self.assertIn("Opción '9' no válida", output)
        self.assertIn("no puede estar vacío", output)
        self.assertIn("Servicio 'prestamo' no válido", output)
        self.assertIn("No hay clientes esperando para 'gestion_cuenta'", output)
        self.assertIn("No hay clientes esperando para 'deposito'", output)
        self.assertIn("Ticket emitido: #1 Beto (retiro)", output)
        self.assertTrue(output.endswith("Hasta luego."))
        # Solo la emisión válida consumió número y encoló un ticket.
        self.assertEqual(queue.stats()["total"], 1)
        self.assertEqual(queue.peek_next("retiro").number, 1)

    def test_call_peek_list_and_stats_options(self):
        queue = BranchQueue()
        queue.issue_ticket("Ana", "retiro")
        queue.issue_ticket("Beto", "retiro")

        queue, output = self.run_session(
            "3", "2",  # ver siguiente en retiro
            "2", "2",  # llamar en retiro
            "4",
            "5",
            "6",
            queue=queue,
        )

        self.assertIn("Siguiente en espera: #1 Ana", output)
        self.assertIn("Llamando a: #1 Ana", output)
        self.assertIn("retiro (1):", output)
        self.assertIn("(sin clientes en espera)", output)
        self.assertIn("total: 1", output)
        self.assertEqual(queue.peek_next("retiro").client_name, "Beto")

    def test_eof_exits_cleanly(self):
        queue, output = self.run_session("1", "Ana")  # EOF al pedir el servicio

        self.assertTrue(output.endswith("Hasta luego."))
        self.assertEqual(queue.stats()["total"], 0)


if __name__ == "__main__":
    unittest.main()
