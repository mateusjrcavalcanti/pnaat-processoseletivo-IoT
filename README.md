# Processo Seletivo – Intensivo Maker | IoT

## Identificação do Candidato

- **Nome completo:** Mateus Junior de Macedo Cavalcanti
- **GitHub:** https://github.com/mateusjrcavalcanti

## Visão Geral da Solução

Este projeto é um sistema de monitoramento para geladeiras, estufas ou painéis elétricos. A ideia é simples: usar um sensor de temperatura (MPU6050) e um botão que simula se a porta está fechada ou não. O sistema monitora duas condições ao mesmo tempo: se a porta ficou aberta por tempo excessivo e se a temperatura subiu de forma abrupta. Se algo der errado, ele emite um alerta pela Serial. Quando tudo volta ao normal, ele também avisa.

## Arquitetura do Sistema Embarcado

O código principal está no `main.py` e foi dividido em 5 funções para não concentrar toda a lógica em um único bloco. O programa executa um loop a cada 100ms — isso é importante para não travar e não perder os comandos que o simulador envia durante os testes.

### Como o programa funciona

1. **Inicialização:** configura o I2C nos pinos 21 e 22 para comunicar com o MPU6050, configura o botão no pino 13 com pull-down interno, e envia a mensagem `"Sistema de Monitoramento Inicializado"`.
2. **No loop principal:**
   - Lê a temperatura. Se der erro na leitura, mantém a última temperatura válida em vez de travar.
   - Verifica se a temperatura atual passou do limite de 3.0°C em relação à referência. Se passou e o alarme ainda não foi disparado, emite o alerta térmico.
   - Verifica se o botão está solto (porta aberta). Se estiver, começa a contar o tempo. Se passar de 5 segundos, dispara o alarme de porta.
   - Recalcula se está em alarme, verificando as duas flags depois dos blocos de verificação. Essa ordem é essencial: se calcular antes, o código pode achar que não está em alarme e atualizar a temperatura de referência com o valor do pico, fazendo o sistema normalizar sem motivo.
   - Tenta normalizar: se estiver em alarme, a porta estiver fechada e a temperatura estiver dentro do limite seguro (< 3.0°C de variação), envia `"Status: Sistema Normalizado."` e redefine todos os valores.
   - Se a porta estiver fechada e não estiver em alarme, atualiza a referência com a temperatura atual.

### Funções do código

- `ler_temperatura()` — lê o MPU6050 pelo I2C e converte o valor. Se falhar, retorna `None`.
- `porta_esta_fechada()` — verifica se o botão está pressionado.
- `verificar_alarme_termico(variacao, ja_disparado)` — compara a variação com o limite de 3.0°C.
- `verificar_alarme_porta(inicio, tempo_atual, ja_disparado)` — controla o cronômetro da porta aberta.
- `normalizar_sistema(...)` — decide se pode normalizar e retorna os valores atualizados.

### Estados do sistema

| Estado | Quando entra | O que faz |
|---|---|---|
| Normal | Inicialização ou depois de normalizar | Monitora e atualiza a referência |
| Alarme de Porta | Porta aberta por 5s ou mais | Mostra `"ALERTA: Porta aberta por muito tempo!"` |
| Alarme Térmico | Temperatura subiu 3.0°C ou mais | Mostra `"ALERTA: Degradacao termica detectada!"` |
| Normalização | Porta fechada e temperatura voltou ao normal | Mostra `"Status: Sistema Normalizado."` e limpa os alarmes |

## Componentes Utilizados na Simulação

| Componente | ID | Função |
|---|---|---|
| ESP32 DevKit C v4 | `esp` | Placa que executa o firmware |
| MPU6050 | `imu1` | Sensor de temperatura (I2C nos pinos 21 e 22) |
| Pushbutton | `btn1` | Simula o sensor de porta (pino 13) |
| Serial Monitor | `$serialMonitor` | Onde as mensagens de alerta aparecem |

## Decisões Técnicas

**Loop sem bloqueio.** Usei `time.sleep_ms(100)` para dar tempo do simulador enviar os comandos entre uma verificação e outra. Se usasse `sleep(5)` por exemplo, o CI perderia a janela de trocar a temperatura e o teste falharia.

**Ordem das verificações importa.** Os alarmes são checados primeiro, e só depois que `em_alarme` é recalculado. Se fizesse ao contrário, na mesma rodada em que o alarme térmico disparasse, a referência seria atualizada para o valor do pico, e na rodada seguinte o sistema normalizaria achando que a temperatura está estável — mesmo estando ainda alta.

**Pull-down no botão.** Conectei o botão no 3V3 e usei `Pin.PULL_DOWN`. Assim, quando o botão está pressionado o pino lê 1 (porta fechada), e quando está solto lê 0 (porta aberta). Isso corresponde exatamente ao que o teste espera: `pressed: 1` = fechada.

**Proteção contra falha no sensor.** Coloquei try/except na leitura. Se o I2C falhar, a função retorna `None` e o programa mantém a última temperatura válida. Não trava.

**Referência atualiza sozinha.** Enquanto está tudo normal e a porta fechada, a referência vai se ajustando à temperatura ambiente. Isso permite que o CI mude a temperatura base (ex: de 20°C para 24°C) e o alarme dispare pela variação.

**Constantes no topo.** `LIMITE_TEMPO_PORTA_ABERTA` e `LIMITE_VARIACAO_TEMPERATURA` ficam nas primeiras linhas. Se precisar mudar os valores depois, não precisa procurar no meio do código.

**Alarme só dispara uma vez.** As flags `alarme_porta_disparado` e `alarme_termico_disparado` impedem a repetição. Quando normaliza, elas são redefinidas e o alarme pode disparar novamente se algo acontecer.

## Resultados Obtidos

Os três testes do CI passaram e ainda executei mais oito situações extras por conta própria.

### Testes do Wokwi CI

1. **Porta aberta:** o sistema aguarda exatamente 5 segundos antes de disparar o alarme. Antes disso, não dispara.
2. **Subida de temperatura:** quando a temperatura vai de 20°C para 24°C, o alarme térmico dispara. E o sistema **não** normaliza enquanto a temperatura continua alta.
3. **Volta ao normal:** depois de um alarme de porta, quando a porta fecha, o sistema mostra a mensagem de normalização.

### Testes extras que executei

| Situação | Resultado |
|---|---|
| Porta abre e fecha em menos de 5s | Não dispara alarme |
| Variação de exatamente 3.0°C | Dispara alarme |
| Variação de 2.9°C | Não dispara (está abaixo do limite) |
| Porta aberta e temperatura alta ao mesmo tempo | Dispara os dois alarmes |
| Fecha a porta mas temperatura continua alta | Não normaliza (precisa das duas condições) |
| Depois de normalizar, temperatura sobe de novo | Alarme dispara outra vez |
| Erro na leitura I2C | Não trava, usa a última temperatura |
| Alarme térmico dispara, abre a porta, fecha a porta | Somente normaliza quando a temperatura também volta |

## Comentários Adicionais

A parte mais difícil foi acertar o timing entre a captura da temperatura de referência e os comandos que o CI envia. No começo eu tinha um bug: a referência era atualizada antes do alarme ser conferido, então quando a temperatura subia, o sistema normalizava no mesmo instante. Levei um tempo para perceber que era só uma questão de ordem das linhas no loop.

Com mais tempo disponível, eu colocaria um filtro de média nas leituras de temperatura — pegar as últimas 3 medições e tirar a média — para evitar alarme falso com ruído.

O que mais aprendi nesse projeto foi a importância de não usar funções que travam o loop e de alinhar as strings exatamente como o teste espera. Qualquer letra maiúscula ou minúscula diferente já faz o CI reprovar.
