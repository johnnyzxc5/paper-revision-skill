# Paper Revision

[English](README.md) · [Licencia MIT](LICENSE) · [Contribuir](CONTRIBUTING.md)

Una skill para que tu agente te ayude a escribir, revisar y auditar papers
científicos preservando la relación entre afirmaciones y evidencia. Incluye
instrucciones, referencias, herramientas Python y pruebas. Puedes usarla con
tus propios papers, datos, revisores, revistas y fuentes; no depende de un
proyecto o una biblioteca de NotebookLM concreta. Las herramientas de documento
están especialmente preparadas para LaTeX.

## Pídele a tu agente que la instale

```text
Instala Paper Revision desde https://github.com/johnnyzxc5/paper-revision-skill.
Lee el README e instala la carpeta completa paper-revision, con sus scripts y
referencias, en el directorio de skills de este agente. Conserva cualquier
instalación existente. Empieza con el flujo local y configura NotebookLM solo
si te lo pido.
```

O hazlo manualmente con Python 3.10+ y Git:

```sh
git clone https://github.com/johnnyzxc5/paper-revision-skill.git
cd paper-revision-skill
python install.py --agent codex
```

Para Claude usa `--agent claude`; para otra ubicación usa
`--dest /ruta/al/directorio/de/skills`. El instalador no descarga dependencias
ni configura credenciales. Si ya está instalada, se detiene; `--update` conserva
una copia ZIP antes de sustituirla. Los destinos y detalles están en el
[README principal](README.md).

## Úsala con tu paper

```text
Usa $paper-revision para auditar manuscript.tex y references.bib. Quiero aclarar
la contribución y el alcance de la evidencia. No edites todavía; presenta los
problemas materiales con sus ubicaciones. Este paper no tiene revisores.
```

```text
Usa $paper-revision para revisar esta sección con mis comentarios de revisión.
Comprueba los datos y el código, conserva las cifras y la notación, y presenta
la estrategia de corrección y el texto exacto para aprobarlo.
```

El flujo por defecto pide al autor elegir la estrategia para cambios sustantivos
y aprobar después el texto exacto. Comprueba lo aplicado y la compilación.
Las instrucciones explícitas del autor y las reglas del agente controlan la
autorización. Una auditoría no modifica el paper y no se inventan revisores,
citas, resultados ni evidencia que falte.

## ¿Hace falta notebooklm-py?

**Para trabajar localmente, no.** Las herramientas locales usan la biblioteca
estándar de Python. La compilación depende de las herramientas de tu paper.

**Para usar la integración de NotebookLM, sí.** Basta con instalar el paquete
[notebooklm-py](https://github.com/teng-lin/notebooklm-py) e iniciar sesión con tu
propia cuenta Google. No hace falta clonar su repositorio ni instalar otra skill
o un servidor MCP. Esta integración usa la sesión del cliente, no una API key
de NotebookLM dentro de la skill.

La [guía de configuración](paper-revision/references/notebooklm-setup.md) explica
los pasos para Windows, macOS y Linux. Los ejemplos de notebooks están vacíos.
Tú eliges tus fuentes y los roles de contexto del proyecto, evidencia técnica
y escritura. La biblioteca de escritura incluida es un ejemplo configurable;
no se distribuyen libros ni PDFs. El cliente es comunitario y usa endpoints
no documentados, por lo que su compatibilidad puede cambiar.

Mantén tu configuración, credenciales, manuscritos, prompts y recibos en un
espacio privado y exclúyelo de Git. Conectar NotebookLM no autoriza por sí mismo
subir un paper inédito. Un veredicto del notebook tampoco prueba que una
afirmación científica sea correcta.

## Puedes usarla y mejorarla

La licencia MIT permite usarla, modificarla, redistribuirla y utilizarla
comercialmente conservando el aviso de licencia. No exige citar la skill en
tu paper. Los paquetes externos y los libros mantienen sus propias licencias.
Puedes abrir issues, proponer cambios o hacer un fork; consulta
[CONTRIBUTING.md](CONTRIBUTING.md) para ejecutar las pruebas.
