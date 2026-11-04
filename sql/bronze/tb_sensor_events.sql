CREATE TABLE IF NOT EXISTS datapulse.bronze.sensor_events (
    str_registro_id STRING
        COMMENT 'Identificador do registro',

    str_data_registro STRING
        COMMENT 'Data do registro',

    str_linha_producao STRING
        COMMENT 'Linha de produção associada ao registro',

    str_turno STRING
        COMMENT 'Turno de produção',

    str_maquina STRING
        COMMENT 'Máquina associada ao registro',

    int_idade_maquina_anos BIGINT
        COMMENT 'Idade da máquina em anos',

    dbl_temperatura_valor DOUBLE
        COMMENT 'Valor da temperatura',

    str_unidade_temperatura STRING
        COMMENT 'Unidade de medida da temperatura',

    dbl_pressao_valor DOUBLE
        COMMENT 'Valor da pressão',

    str_unidade_pressao STRING
        COMMENT 'Unidade de medida da pressão',

    str_vibracao_motor_mm_s STRING
        COMMENT 'Vibração do motor em milímetros por segundo',

    dbl_velocidade_esteira_m_min DOUBLE
        COMMENT 'Velocidade da esteira em metros por minuto',

    dbl_umidade_pct DOUBLE
        COMMENT 'Umidade em percentual',

    int_tamanho_lote BIGINT
        COMMENT 'Tamanho do lote',

    dbl_tempo_setup_min DOUBLE
        COMMENT 'Tempo de setup em minutos',

    int_paradas_nao_planejadas BIGINT
        COMMENT 'Quantidade de paradas não planejadas',

    dbl_taxa_defeitos_pct DOUBLE
        COMMENT 'Taxa de defeitos em percentual',

    dbl_energia_sensor_b_kwh DOUBLE
        COMMENT 'Energia do sensor B em quilowatt-hora',

    str_codigo_campanha STRING
        COMMENT 'Código da campanha',

    dbl_ruido_aleatorio DOUBLE
        COMMENT 'Valor de ruído aleatório',

    str_consumo_energia_kwh STRING
        COMMENT 'Consumo de energia em quilowatt-hora',

    int_falha_24h BIGINT
        COMMENT 'Indicador de falha nas últimas 24 horas'
)
USING DELTA
COMMENT 'Registros de sensores e métricas de produção industrial';
