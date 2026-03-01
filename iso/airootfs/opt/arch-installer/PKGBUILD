# Maintainer: broncbash <https://gitlab.com/broncbash>
pkgname=arch-installer
pkgver=0.1.0
pkgrel=1
pkgdesc="Full-featured GTK3 graphical installer for Arch Linux"
arch=('any')
url="https://gitlab.com/broncbash/arch-installer"
license=('GPL3')
depends=(
    'python'
    'python-gobject'
    'gtk3'
    'polkit'
    'parted'
    'arch-install-scripts'   # provides pacstrap, arch-chroot, genfstab
)
optdepends=(
    'ttf-jetbrains-mono: preferred monospace font for the UI'
    'polkit-gnome: polkit agent for non-KDE/GNOME desktops'
    'reflector: for automatic mirror ranking'
)
source=("$pkgname-$pkgver.tar.gz::https://gitlab.com/broncbash/$pkgname/-/archive/v$pkgver/$pkgname-v$pkgver.tar.gz")
sha256sums=('SKIP')

package() {
    cd "$srcdir/$pkgname-v$pkgver"

    # Main package
    install -dm755 "$pkgdir/usr/lib/$pkgname"
    cp -r installer "$pkgdir/usr/lib/$pkgname/"

    # Launcher script
    install -Dm755 /dev/stdin "$pkgdir/usr/bin/arch-installer" <<EOF
#!/bin/bash
exec python /usr/lib/$pkgname/installer/main.py "\$@"
EOF

    # Icons
    install -Dm644 installer/assets/installer.svg \
        "$pkgdir/usr/share/icons/hicolor/scalable/apps/$pkgname.svg"
    install -Dm644 installer/assets/installer.png \
        "$pkgdir/usr/share/icons/hicolor/128x128/apps/$pkgname.png"

    # Desktop entry
    install -Dm644 arch-installer.desktop \
        "$pkgdir/usr/share/applications/$pkgname.desktop"

    # License + docs
    install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
    install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
}
