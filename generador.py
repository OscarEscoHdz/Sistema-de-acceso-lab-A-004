import qrcode

matricula = "22-003-1234" # Cambia esto por la matrícula que quieras probar
imagen_qr = qrcode.make(matricula)
imagen_qr.save(f"{matricula}.png")

print(f"Código QR generado y guardado como {matricula}.png")