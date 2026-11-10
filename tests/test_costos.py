from scripts.costos import cdn_norteamerica, egress_gb, fleet_servers


def test_buffer_se_calcula_sobre_la_flota_total():
    assert fleet_servers(1000) == 125
    assert fleet_servers(4300) == 538


def test_egress_decimal_y_tarifa_por_gib():
    assert egress_gb(20000, 6000, 3600) == 54000
    assert egress_gb(500, 800, 300) == 15
    assert cdn_norteamerica(10240 + 100) == 819.2 + 5.5
