document.addEventListener('DOMContentLoaded', () => {
    // ── Mostrar flash messages como toasts de SweetAlert2 ──
    (function showFlashMessages() {
        var container = document.getElementById('flash-messages');
        if (!container) return;
        var raw = container.getAttribute('data-messages');
        if (!raw || raw === '[]' || raw === '') return;
        try {
            var messages = JSON.parse(raw);
            if (!Array.isArray(messages)) return;
            messages.forEach(function(item) {
                var category = item[0] || 'info';
                var message = item[1] || '';
                var iconMap = { 'success': 'success', 'danger': 'error', 'error': 'error', 'warning': 'warning', 'info': 'info' };
                var icon = iconMap[category] || 'info';
                var toast = Swal.mixin({
                    toast: true,
                    position: 'top-end',
                    showConfirmButton: false,
                    timer: 4000,
                    timerProgressBar: true,
                    background: '#1a1714',
                    color: '#e8ddd0',
                    iconColor: category === 'danger' ? '#d4554a' : '#d4874a',
                    didOpen: function(toast) {
                        toast.addEventListener('mouseenter', Swal.stopTimer);
                        toast.addEventListener('mouseleave', Swal.resumeTimer);
                    }
                });
                toast.fire({ icon: icon, title: message });
            });
        } catch(e) {
            console.warn('Error parsing flash messages:', e);
        }
    })();

    // ── SweetAlert2 para botones de eliminar ──
    document.addEventListener('click', function(e) {
        var target = e.target.closest('button[onclick]');
        if (!target) return;
        var onclickAttr = target.getAttribute('onclick');
        if (!onclickAttr || !onclickAttr.includes('confirm')) return;
        
        // Prevenir el confirm nativo
        e.preventDefault();
        e.stopPropagation();
        
        var msg = '¿Estás seguro?';
        var match = onclickAttr.match(/confirm\s*\(\s*'([^']+)'\s*\)/);
        if (match) msg = match[1];
        
        Swal.fire({
            title: '¿Confirmar?',
            text: msg,
            icon: 'question',
            showCancelButton: true,
            confirmButtonColor: '#d4554a',
            cancelButtonColor: '#d4874a',
            confirmButtonText: 'Sí, eliminar',
            cancelButtonText: 'Cancelar',
            background: '#1a1714',
            color: '#e8ddd0',
            iconColor: '#d4554a',
            reverseButtons: true
        }).then(function(result) {
            if (result.isConfirmed) {
                // Remover el onclick para evitar loop y hacer submit
                target.removeAttribute('onclick');
                target.click();
            }
        });
    });

    // ── Cerrar sesión con SweetAlert2 ──
    var dropdownItems = document.querySelectorAll('.dropdown-item');
    dropdownItems.forEach(function(item) {
        if (item.getAttribute('href') && item.getAttribute('href').includes('logout')) {
            item.addEventListener('click', function(e) {
                e.preventDefault();
                Swal.fire({
                    title: 'Cerrar Sesión',
                    text: '¿Estás seguro que deseas cerrar sesión?',
                    icon: 'question',
                    showCancelButton: true,
                    confirmButtonColor: '#d4874a',
                    cancelButtonColor: '#6c757d',
                    confirmButtonText: 'Sí, cerrar sesión',
                    cancelButtonText: 'Cancelar',
                    background: '#1a1714',
                    color: '#e8ddd0',
                    iconColor: '#d4874a',
                    reverseButtons: true
                }).then(function(result) {
                    if (result.isConfirmed) {
                        window.location.href = item.getAttribute('href');
                    }
                });
            });
        }
    });

    // ── Sidebar collapse toggle ──
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.querySelector('.sidebar');
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
        });
    }

    // ── Avatar: intentar cargar la foto, si falla se quedan las iniciales ──
    const avatarImg = document.querySelector('.avatar-img');
    const avatarInitials = document.querySelector('.avatar-initials');
    if (avatarImg) {
        avatarImg.addEventListener('load', () => {
            avatarImg.style.display = 'block';
            if (avatarInitials) avatarInitials.style.display = 'none';
        });
        avatarImg.addEventListener('error', () => {
            avatarImg.style.display = 'none';
            if (avatarInitials) avatarInitials.style.display = '';
        });
        if (avatarImg.complete && avatarImg.naturalHeight > 0) {
            avatarImg.style.display = 'block';
            if (avatarInitials) avatarInitials.style.display = 'none';
        }
    }

    // ── User dropdown toggle ──
    const dropdownToggle = document.getElementById('userDropdownToggle');
    const dropdownMenu = document.getElementById('userDropdownMenu');
    if (dropdownToggle && dropdownMenu) {
        dropdownToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = dropdownMenu.classList.toggle('show');
            dropdownToggle.setAttribute('aria-expanded', isOpen);
        });

        document.addEventListener('click', (e) => {
            if (!dropdownToggle.contains(e.target) && !dropdownMenu.contains(e.target)) {
                dropdownMenu.classList.remove('show');
                dropdownToggle.setAttribute('aria-expanded', 'false');
            }
        });
    }

    // ── Heartbeat ──
    setInterval(() => {
        fetch('/heartbeat', { method: 'POST' }).catch(() => {});
    }, 2000);

    // ── Cerrar sesión al cerrar el navegador ──
    // Cuando la pestaña se oculta (cierre real o cambio de pestaña),
    // enviamos un heartbeat extra. Si TODAS las pestañas se cierran,
    // el heartbeat deja de llegar y el servidor se apaga en 10s.
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            // Enviar heartbeat final via sendBeacon (funciona en unload)
            navigator.sendBeacon('/heartbeat', '');
        }
    });

    // ── Submenú: toggle desplegable ──
    document.querySelectorAll('.submenu-toggle').forEach(function(toggle) {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            var targetId = this.getAttribute('data-target');
            var submenu = document.getElementById(targetId);
            if (submenu) {
                submenu.classList.toggle('expanded');
                this.classList.toggle('expanded');
            }
        });
    });
});
