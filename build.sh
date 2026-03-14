#!/usr/bin/bash

cd "$(git rev-parse --show-toplevel)"

PROG='czu'
PREFIX="${PROG}"
BINDIR="${PREFIX}/bin"
ENTRYPOINT='codezipupdate.py'
RAW_LIBDIR="/lib/${PROG}"
LIBDIR="${PREFIX}/${RAW_LIBDIR}"
DOCDIR="${PREFIX}/share/doc/${PROG}"

rm -rf "${PREFIX}"
mkdir -p "${PREFIX}" "${BINDIR}" "${LIBDIR}" "${DOCDIR}"

( shopt -s dotglob; cp -R src/* "${LIBDIR}"; )
cat > "${BINDIR}/czu" << EOF
#!/usr/bin/bash

p="\$(realpath "\$(dirname "\$0")/../${RAW_LIBDIR}/${ENTRYPOINT}")"
if [[ "\${p}" =~ ^/+ ]]; then
	p="\${p##/}"
	p="/\${p}"
fi
exec python -B "\${p}" "\$@"
EOF

cp README.md -t "${DOCDIR}"

tar -c "${PREFIX}" | zstd -9fT0 > "${PROG}.tar.zst"
rm -rf "${PREFIX}"
