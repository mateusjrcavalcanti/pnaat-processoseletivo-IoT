import time
from machine import Pin, I2C

LIMITE_TEMPO_PORTA_ABERTA = 5000
LIMITE_VARIACAO_TEMPERATURA = 3.0

i2c = I2C(0, scl=Pin(22), sda=Pin(21))
ENDERECO_MPU6050 = 0x68
botao_porta = Pin(13, Pin.IN, Pin.PULL_DOWN)


def ler_temperatura():
    try:
        dados = i2c.readfrom_mem(ENDERECO_MPU6050, 0x41, 2)
        valor_bruto = (dados[0] << 8) | dados[1]
        if valor_bruto >= 0x8000:
            valor_bruto -= 0x10000
        return valor_bruto / 340.0 + 36.53
    except Exception:
        return None


def porta_esta_fechada():
    return botao_porta.value() == 1


def verificar_alarme_termico(variacao, ja_disparado):
    if variacao >= LIMITE_VARIACAO_TEMPERATURA and not ja_disparado:
        print("ALERTA: Degradacao termica detectada!")
        return True
    return ja_disparado


def verificar_alarme_porta(inicio, tempo_atual, ja_disparado):
    if inicio == 0:
        inicio = tempo_atual
    decorrido = time.ticks_diff(tempo_atual, inicio)
    if decorrido >= LIMITE_TEMPO_PORTA_ABERTA and not ja_disparado:
        print("ALERTA: Porta aberta por muito tempo!")
        return inicio, True
    return inicio, ja_disparado


def normalizar_sistema(em_alarme, fechada, variacao,
                       referencia, temp_atual, inicio):
    if em_alarme and fechada and variacao < LIMITE_VARIACAO_TEMPERATURA:
        time.sleep_ms(600)
        print("Status: Sistema Normalizado.")
        return temp_atual, temp_atual, False, False, 0
    return referencia, None, None, None, inicio


print("Sistema de Monitoramento Inicializado")

temp_referencia = None
ultima_temperatura = None
inicio_porta_aberta = 0
alarme_porta_disparado = False
alarme_termico_disparado = False

while True:
    temp_atual = ler_temperatura()
    if temp_atual is None:
        temp_atual = ultima_temperatura
    else:
        ultima_temperatura = temp_atual

    if temp_referencia is None:
        if temp_atual is not None:
            temp_referencia = temp_atual
        else:
            time.sleep_ms(100)
            continue

    fechada = porta_esta_fechada()
    variacao = temp_atual - temp_referencia
    agora = time.ticks_ms()

    alarme_termico_disparado = verificar_alarme_termico(
        variacao, alarme_termico_disparado
    )

    if not fechada:
        inicio_porta_aberta, alarme_porta_disparado = verificar_alarme_porta(
            inicio_porta_aberta, agora, alarme_porta_disparado
        )
    else:
        inicio_porta_aberta = 0

    em_alarme = alarme_porta_disparado or alarme_termico_disparado

    ref, _, p_flag, t_flag, inicio_flag = normalizar_sistema(
        em_alarme, fechada, variacao,
        temp_referencia, temp_atual, inicio_porta_aberta
    )
    if p_flag is not None:
        temp_referencia = ref
        alarme_porta_disparado = p_flag
        alarme_termico_disparado = t_flag
        inicio_porta_aberta = inicio_flag

    if fechada and not em_alarme:
        temp_referencia = temp_atual

    time.sleep_ms(100)
