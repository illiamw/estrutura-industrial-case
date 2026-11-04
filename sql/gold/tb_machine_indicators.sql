CREATE TABLE IF NOT EXISTS datapulse.gold.sensor_events (
    dbl_paradas_nao_planejadas DOUBLE
        COMMENT 'Quantidade de paradas não planejadas',

    dbl_idade_maquina_anos DOUBLE
        COMMENT 'Idade da máquina em anos',

    dbl_temperatura_c DOUBLE
        COMMENT 'Temperatura em graus Celsius',

    dbl_pressao_bar DOUBLE
        COMMENT 'Pressão em bar',

    dbl_vibracao_motor_mm_s DOUBLE
        COMMENT 'Vibração do motor em milímetros por segundo',

    dbl_velocidade_esteira_m_min DOUBLE
        COMMENT 'Velocidade da esteira em metros por minuto',

    dbl_umidade_pct DOUBLE
        COMMENT 'Umidade em percentual',

    dbl_tamanho_lote DOUBLE
        COMMENT 'Tamanho do lote',

    dbl_tempo_setup_min DOUBLE
        COMMENT 'Tempo de setup em minutos',

    dbl_taxa_defeitos_pct DOUBLE
        COMMENT 'Taxa de defeitos em percentual',

    dbl_linha_producao_pad_A DOUBLE
        COMMENT 'Indicador da linha de produção padronizada A',

    dbl_linha_producao_pad_B DOUBLE
        COMMENT 'Indicador da linha de produção padronizada B',

    dbl_linha_producao_pad_C DOUBLE
        COMMENT 'Indicador da linha de produção padronizada C',

    dbl_turno_pad_manha DOUBLE
        COMMENT 'Indicador do turno padronizado da manhã',

    dbl_turno_pad_noite DOUBLE
        COMMENT 'Indicador do turno padronizado da noite',

    dbl_turno_pad_tarde DOUBLE
        COMMENT 'Indicador do turno padronizado da tarde',

    dbl_maquina_M01 DOUBLE
        COMMENT 'Indicador da máquina M01',

    dbl_maquina_M02 DOUBLE
        COMMENT 'Indicador da máquina M02',

    dbl_maquina_M03 DOUBLE
        COMMENT 'Indicador da máquina M03',

    dbl_maquina_M04 DOUBLE
        COMMENT 'Indicador da máquina M04',

    dbl_maquina_M05 DOUBLE
        COMMENT 'Indicador da máquina M05',

    dbl_maquina_M06 DOUBLE
        COMMENT 'Indicador da máquina M06',

    dbl_maquina_M07 DOUBLE
        COMMENT 'Indicador da máquina M07',

    dbl_maquina_M08 DOUBLE
        COMMENT 'Indicador da máquina M08',

    dbl_consumo_energia_kwh DOUBLE
        COMMENT 'Consumo de energia em quilowatt-hora',

    int_falha_24h BIGINT
        COMMENT 'Indicador de falha nas últimas 24 horas',

    ts_data_registro_pad TIMESTAMP
        COMMENT 'Data e horário do registro padronizado'
)
USING DELTA
COMMENT 'Eventos de sensores agregados e codificados na camada gold';
