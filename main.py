"""Sistema de gestión de clientes, servicios y reservas - Software FJ.

Fase 4 - Programación UNAD. Demostración académica sin base de datos.
Ejecutar: python main.py
Los datos de trabajo viven en listas; eventos y errores se registran en eventos.log.
"""

from abc import ABC, abstractmethod
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import logging
import re
from typing import overload


logging.basicConfig(
    filename="eventos.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8",
)


# Excepciones personalizadas para distinguir errores del sistema.
class ErrorSistema(Exception):
    """Error controlado de la aplicación."""


class DatosInvalidos(ErrorSistema):
    """Dato obligatorio ausente o con formato inválido."""


class ElementoDuplicado(ErrorSistema):
    """Un identificador ya fue registrado."""


class ElementoNoEncontrado(ErrorSistema):
    """No se encontró el elemento solicitado."""


class ServicioNoDisponible(ErrorSistema):
    """El servicio no está disponible para reservar."""


class ReservaInvalida(ErrorSistema):
    """Datos no aptos para crear o procesar una reserva."""


class OperacionNoPermitida(ErrorSistema):
    """La operación no es válida para el estado actual."""


def entero_positivo(valor, campo):
    """Valida que el dato sea un entero positivo y no un booleano."""
    if isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0:
        raise DatosInvalidos(f"{campo} debe ser un entero mayor que cero.")
    return valor


def dinero(valor, campo="tarifa"):
    """Convierte importes numéricos a Decimal, evitando errores de float."""
    try:
        resultado = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError) as causa:
        raise DatosInvalidos(f"{campo} debe ser un número válido.") from causa
    if not resultado.is_finite() or resultado < 0:
        raise DatosInvalidos(f"{campo} no puede ser negativo ni infinito.")
    return resultado


class Entidad(ABC):
    """Clase abstracta base para entidades identificables."""

    def __init__(self, identificador):
        if not isinstance(identificador, str) or not identificador.strip():
            raise DatosInvalidos("El identificador es obligatorio.")
        self._identificador = identificador.strip()

    @property
    def identificador(self):
        return self._identificador

    @abstractmethod
    def describir(self):
        """Devuelve una descripción de la entidad."""


class Cliente(Entidad):
    """Cliente con datos encapsulados y validados."""

    def __init__(self, identificador, nombre, correo):
        super().__init__(identificador)
        self.nombre = nombre
        self.correo = correo

    @property
    def nombre(self):
        return self.__nombre

    @nombre.setter
    def nombre(self, valor):
        if not isinstance(valor, str) or len(valor.strip()) < 3:
            raise DatosInvalidos("El nombre del cliente debe tener al menos 3 caracteres.")
        self.__nombre = valor.strip()

    @property
    def correo(self):
        return self.__correo

    @correo.setter
    def correo(self, valor):
        if not isinstance(valor, str) or not re.fullmatch(
            r"[^\s@]+@[^\s@]+\.[^\s@]+", valor.strip()
        ):
            raise DatosInvalidos("El correo electrónico no tiene un formato válido.")
        self.__correo = valor.strip()

    def describir(self):
        return f"Cliente {self.identificador}: {self.nombre} ({self.correo})"


class Servicio(Entidad, ABC):
    """Clase abstracta: los tipos de servicio implementan sus reglas."""

    def __init__(self, identificador, nombre, tarifa, disponible=True):
        super().__init__(identificador)
        if not isinstance(nombre, str) or not nombre.strip():
            raise DatosInvalidos("El nombre del servicio es obligatorio.")
        if not isinstance(disponible, bool):
            raise DatosInvalidos("La disponibilidad debe ser True o False.")
        self._nombre = nombre.strip()
        self._tarifa = dinero(tarifa)
        self.disponible = disponible

    @abstractmethod
    def validar_parametros(self):
        """Valida las características específicas del servicio."""

    @abstractmethod
    def calcular_costo(self, duracion):
        """Calcula el costo base según el tipo de servicio."""

    @abstractmethod
    def describir(self):
        """Describe los detalles específicos del servicio."""

    # Firmas tipadas de sobrecarga; la implementación usa argumentos opcionales.
    @overload
    def cotizar(self, duracion: int) -> Decimal: ...

    @overload
    def cotizar(self, duracion: int, descuento: int | float | Decimal) -> Decimal: ...

    @overload
    def cotizar(
        self, duracion: int, descuento: int | float | Decimal,
        impuesto: int | float | Decimal,
    ) -> Decimal: ...

    def cotizar(self, duracion, descuento=0, impuesto=0):
        """Cotiza con porcentaje de descuento e impuesto opcionales."""
        d = dinero(descuento, "descuento")
        i = dinero(impuesto, "impuesto")
        if d > 100 or i > 100:
            raise DatosInvalidos("Descuento e impuesto deben estar entre 0 y 100.")
        base = self.calcular_costo(duracion)
        total = base * (Decimal("1") - d / 100) * (Decimal("1") + i / 100)
        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class Sala(Servicio):
    """Alquiler de sala por horas."""

    def __init__(self, identificador, nombre, tarifa_hora, capacidad, disponible=True):
        super().__init__(identificador, nombre, tarifa_hora, disponible)
        self.capacidad = capacidad
        self.validar_parametros()

    def validar_parametros(self):
        entero_positivo(self.capacidad, "La capacidad")

    def calcular_costo(self, duracion):
        entero_positivo(duracion, "La duración en horas")
        return self._tarifa * duracion

    def describir(self):
        return f"Sala {self._nombre}: {self.capacidad} personas, tarifa por hora ${self._tarifa}"


class Equipo(Servicio):
    """Alquiler de un número de equipos por días."""

    def __init__(self, identificador, nombre, tarifa_dia, cantidad, disponible=True):
        super().__init__(identificador, nombre, tarifa_dia, disponible)
        self.cantidad = cantidad
        self.validar_parametros()

    def validar_parametros(self):
        entero_positivo(self.cantidad, "La cantidad de equipos")

    def calcular_costo(self, duracion):
        entero_positivo(duracion, "La duración en días")
        return self._tarifa * duracion * self.cantidad

    def describir(self):
        return f"Equipo {self._nombre}: {self.cantidad} unidades, tarifa diaria ${self._tarifa} por unidad"


class Asesoria(Servicio):
    """Asesoría especializada por horas."""

    def __init__(self, identificador, nombre, tarifa_hora, especialidad, disponible=True):
        super().__init__(identificador, nombre, tarifa_hora, disponible)
        self.especialidad = especialidad
        self.validar_parametros()

    def validar_parametros(self):
        if not isinstance(self.especialidad, str) or not self.especialidad.strip():
            raise DatosInvalidos("La especialidad de la asesoría es obligatoria.")

    def calcular_costo(self, duracion):
        entero_positivo(duracion, "La duración en horas")
        return self._tarifa * duracion

    def describir(self):
        return f"Asesoría {self._nombre}: {self.especialidad}, tarifa por hora ${self._tarifa}"


class Reserva(Entidad):
    """Relaciona un cliente y un servicio; controla cambios de estado."""

    def __init__(self, identificador, cliente, servicio, duracion):
        super().__init__(identificador)
        if not isinstance(cliente, Cliente) or not isinstance(servicio, Servicio):
            raise ReservaInvalida("Se requieren un cliente y un servicio válidos.")
        try:
            entero_positivo(duracion, "La duración")
        except DatosInvalidos as causa:
            raise ReservaInvalida("La reserva tiene una duración inválida.") from causa
        self.cliente = cliente
        self.servicio = servicio
        self.duracion = duracion
        self.estado = "PENDIENTE"
        self.total = Decimal("0.00")

    def procesar(self, descuento=0, impuesto=0):
        """Procesa una reserva con validaciones y manejo de errores."""
        if self.estado != "PENDIENTE":
            raise OperacionNoPermitida("Solo se procesan reservas pendientes.")
        if not self.servicio.disponible:
            raise ServicioNoDisponible("No es posible reservar un servicio no disponible.")
        try:
            self.total = self.servicio.cotizar(self.duracion, descuento, impuesto)
        except DatosInvalidos as causa:
            raise ReservaInvalida("No se pudo calcular el valor de la reserva.") from causa
        self.estado = "CONFIRMADA"
        logging.info("Reserva %s confirmada; total: %s", self.identificador, self.total)
        return self

    def cancelar(self):
        if self.estado == "CANCELADA":
            raise OperacionNoPermitida("La reserva ya estaba cancelada.")
        self.estado = "CANCELADA"
        logging.info("Reserva %s cancelada", self.identificador)
        return self

    def describir(self):
        return (
            f"Reserva {self.identificador} | {self.cliente.nombre} | "
            f"{self.servicio._nombre} | {self.estado} | Total ${self.total}"
        )


class Gestor:
    """Gestión de objetos en listas en memoria, sin base de datos."""

    def __init__(self):
        self.clientes = []
        self.servicios = []
        self.reservas = []

    def agregar_cliente(self, identificador, nombre, correo):
        if any(c.identificador == identificador for c in self.clientes):
            raise ElementoDuplicado(f"Ya existe el cliente {identificador}.")
        cliente = Cliente(identificador, nombre, correo)
        self.clientes.append(cliente)
        return cliente.describir()

    def agregar_servicio(self, servicio):
        if not isinstance(servicio, Servicio):
            raise DatosInvalidos("Se requiere un servicio válido.")
        if any(s.identificador == servicio.identificador for s in self.servicios):
            raise ElementoDuplicado(f"Ya existe el servicio {servicio.identificador}.")
        self.servicios.append(servicio)
        return servicio.describir()

    def buscar_cliente(self, identificador):
        for cliente in self.clientes:
            if cliente.identificador == identificador:
                return cliente
        raise ElementoNoEncontrado(f"No se encontró el cliente {identificador}.")

    def buscar_servicio(self, identificador):
        for servicio in self.servicios:
            if servicio.identificador == identificador:
                return servicio
        raise ElementoNoEncontrado(f"No se encontró el servicio {identificador}.")

    def crear_reserva(self, identificador, id_cliente, id_servicio, duracion, descuento=0, impuesto=0):
        if any(r.identificador == identificador for r in self.reservas):
            raise ElementoDuplicado(f"Ya existe la reserva {identificador}.")
        cliente = self.buscar_cliente(id_cliente)
        servicio = self.buscar_servicio(id_servicio)
        reserva = Reserva(identificador, cliente, servicio, duracion)
        reserva.procesar(descuento, impuesto)
        self.reservas.append(reserva)
        return reserva.describir()

    def cancelar_reserva(self, identificador):
        for reserva in self.reservas:
            if reserva.identificador == identificador:
                reserva.cancelar()
                return reserva.describir()
        raise ElementoNoEncontrado(f"No se encontró la reserva {identificador}.")


def ejecutar_prueba(numero, descripcion, funcion):
    """Try/except/else/finally: controla errores y continúa las pruebas."""
    print(f"\nPrueba {numero:02d} - {descripcion}")
    try:
        resultado = funcion()
    except ErrorSistema as error:
        logging.exception("Prueba %s con error controlado: %s", numero, error)
        print(f"  ERROR CONTROLADO: {error}")
    except Exception:
        # Evita detener la simulación y conserva el traceback para revisión.
        logging.exception("Prueba %s: error inesperado", numero)
        print("  ERROR INESPERADO: revisar eventos.log")
    else:
        logging.info("Prueba %s completada: %s", numero, descripcion)
        print(f"  CORRECTO: {resultado}")
    finally:
        print("  Fin de operación; aplicación activa.")


def demostracion():
    """Simula operaciones válidas e inválidas requeridas por el Anexo 3."""
    gestor = Gestor()
    casos = [
        ("Registrar cliente válido", lambda: gestor.agregar_cliente("C01", "Ana Torres", "ana@correo.com")),
        ("Rechazar correo inválido", lambda: gestor.agregar_cliente("C02", "Luis Pérez", "correo_incorrecto")),
        ("Rechazar cliente duplicado", lambda: gestor.agregar_cliente("C01", "Ana Torres", "ana@correo.com")),
        ("Registrar segundo cliente", lambda: gestor.agregar_cliente("C03", "Luis Pérez", "luis@correo.com")),
        ("Crear sala válida", lambda: gestor.agregar_servicio(Sala("S01", "Sala Norte", 50000, 12))),
        ("Rechazar sala con capacidad negativa", lambda: gestor.agregar_servicio(Sala("S02", "Sala Sur", 50000, -3))),
        ("Crear alquiler de equipos", lambda: gestor.agregar_servicio(Equipo("E01", "Proyector", 30000, 2))),
        ("Crear asesoría especializada", lambda: gestor.agregar_servicio(Asesoria("A01", "Consultoría", 80000, "Sistemas"))),
        ("Rechazar identificador de servicio repetido", lambda: gestor.agregar_servicio(Sala("S01", "Otra sala", 40000, 8))),
        ("Crear servicio no disponible", lambda: gestor.agregar_servicio(Sala("S03", "Sala en mantenimiento", 25000, 6, False))),
        ("Confirmar reserva de sala", lambda: gestor.crear_reserva("R01", "C01", "S01", 2)),
        ("Rechazar reserva de servicio no disponible", lambda: gestor.crear_reserva("R02", "C01", "S03", 2)),
        ("Rechazar reserva de duración inválida", lambda: gestor.crear_reserva("R03", "C03", "E01", 0)),
        ("Reservar equipos con descuento e impuesto", lambda: gestor.crear_reserva("R04", "C03", "E01", 3, 10, 19)),
        ("Rechazar descuento fuera de rango", lambda: gestor.crear_reserva("R05", "C01", "A01", 1, 120)),
        ("Cancelar reserva existente", lambda: gestor.cancelar_reserva("R01")),
        ("Rechazar segunda cancelación", lambda: gestor.cancelar_reserva("R01")),
        ("Rechazar cliente inexistente", lambda: gestor.crear_reserva("R06", "C99", "S01", 1)),
    ]
    logging.info("Inicio de la simulación académica")
    print("SOFTWARE FJ - GESTIÓN DE CLIENTES, SERVICIOS Y RESERVAS")
    print("Ejecutando 18 pruebas; las fallas intencionales deben ser controladas.")
    for numero, (descripcion, funcion) in enumerate(casos, start=1):
        ejecutar_prueba(numero, descripcion, funcion)
    print("\nRESUMEN FINAL")
    print(f"Clientes registrados: {len(gestor.clientes)}")
    print(f"Servicios registrados: {len(gestor.servicios)}")
    print(f"Reservas confirmadas o canceladas: {len(gestor.reservas)}")
    print("Consulta eventos.log para revisar eventos y errores.")
    logging.info("Fin de la simulación")


if __name__ == "__main__":
    demostracion()

