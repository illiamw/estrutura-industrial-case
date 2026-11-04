CREATE TABLE IF NOT EXISTS datapulse.silver.sensor_events (
    str_registro_id STRING
        COMMENT 'Identificador do registro',

    str_maquina STRING
        COMMENT 'Máquina associada ao registro',

    int_idade_maquina_anos BIGINT
        COMMENT 'Idade da máquina em anos',

    dec_vibracao_motor_mm_s DOUBLE
        COMMENT 'Vibração do motor em milímetros por segundo',

    dec_velocidade_esteira_m_min DOUBLE
        COMMENT 'Velocidade da esteira em metros por minuto',

    dec_umidade_pct DOUBLE
        COMMENT 'Umidade em percentual',

    dec_tamanho_lote DOUBLE
        COMMENT 'Tamanho do lote',

    dec_tempo_setup_min DOUBLE
        COMMENT 'Tempo de setup em minutos',

    int_paradas_nao_planejadas BIGINT
        COMMENT 'Quantidade de paradas não planejadas',

    dec_taxa_defeitos_pct DOUBLE
        COMMENT 'Taxa de defeitos em percentual',

    dec_energia_sensor_b_kwh DOUBLE
        COMMENT 'Energia do sensor B em quilowatt-hora',

    str_codigo_campanha STRING
        COMMENT 'Código da campanha',

    dec_ruido_aleatorio DOUBLE
        COMMENT 'Valor de ruído aleatório',

    dec_consumo_energia_kwh DOUBLE
        COMMENT 'Consumo de energia em quilowatt-hora',

    int_falha_24h BIGINT
        COMMENT 'Indicador de falha nas últimas 24 horas',

    ts_data_registro_pad TIMESTAMP
        COMMENT 'Data e horário do registro padronizado',

    dec_temperatura_c DOUBLE
        COMMENT 'Temperatura em graus Celsius',

    dec_pressao_bar DOUBLE
        COMMENT 'Pressão em bar',

    str_linha_producao_pad STRING
        COMMENT 'Linha de produção padronizada',

    str_turno_pad STRING
        COMMENT 'Turno padronizado'
)
USING DELTA
COMMENT 'Eventos de sensores padronizados na camada silver';
