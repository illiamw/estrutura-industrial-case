CREATE TABLE IF NOT EXISTS datapulse.gold.sensor_events (
    dec_paradas_nao_planejadas DOUBLE
        COMMENT 'Quantidade de paradas não planejadas',

    dec_idade_maquina_anos DOUBLE
        COMMENT 'Idade da máquina em anos',

    dec_temperatura_c DOUBLE
        COMMENT 'Temperatura em graus Celsius',

    dec_pressao_bar DOUBLE
        COMMENT 'Pressão em bar',

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

    dec_taxa_defeitos_pct DOUBLE
        COMMENT 'Taxa de defeitos em percentual',

    dec_linha_producao_pad_a DOUBLE
        COMMENT 'Indicador da linha de produção padronizada A',

    dec_linha_producao_pad_b DOUBLE
        COMMENT 'Indicador da linha de produção padronizada B',

    dec_linha_producao_pad_c DOUBLE
        COMMENT 'Indicador da linha de produção padronizada C',

    dec_turno_pad_manha DOUBLE
        COMMENT 'Indicador do turno padronizado da manhã',

    dec_turno_pad_noite DOUBLE
        COMMENT 'Indicador do turno padronizado da noite',

    dec_turno_pad_tarde DOUBLE
        COMMENT 'Indicador do turno padronizado da tarde',

    dec_maquina_m01 DOUBLE
        COMMENT 'Indicador da máquina M01',

    dec_maquina_m02 DOUBLE
        COMMENT 'Indicador da máquina M02',

    dec_maquina_m03 DOUBLE
        COMMENT 'Indicador da máquina M03',

    dec_maquina_m04 DOUBLE
        COMMENT 'Indicador da máquina M04',

    dec_maquina_m05 DOUBLE
        COMMENT 'Indicador da máquina M05',

    dec_maquina_m06 DOUBLE
        COMMENT 'Indicador da máquina M06',

    dec_maquina_m07 DOUBLE
        COMMENT 'Indicador da máquina M07',

    dec_maquina_m08 DOUBLE
        COMMENT 'Indicador da máquina M08',

    dec_consumo_energia_kwh DOUBLE
        COMMENT 'Consumo de energia em quilowatt-hora',

    big_falha_24h BIGINT
        COMMENT 'Indicador de falha nas últimas 24 horas',

    ts_data_registro_pad TIMESTAMP
        COMMENT 'Data e horário do registro padronizado'
)
USING DELTA
COMMENT 'Eventos de sensores agregados e codificados na camada gold';
