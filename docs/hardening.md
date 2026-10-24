# What bootstrap-server changes, and why

Every step is idempotent: it checks the current state first and only writes when something differs, so the script can be re-run safely (and the CI test fails if a second run changes anything).

| Step | Change | Why |
|---|---|---|
| Packages | `unattended-upgrades fail2ban ufw openssh-server sudo jq curl …` | Baseline tools; nothing that runs a network service except sshd |
| Admin user | creates `deploy`, member of `sudo`, passwordless sudo via a `visudo`-validated drop-in | Key-only accounts have no password to type; a broken sudoers file would lock out root access, so it is validated before it is kept |
| SSH key | appended to `authorized_keys` once, `700`/`600` permissions | sshd silently ignores keys with loose permissions |
| sshd | drop-in `sshd_config.d/10-hardening.conf`: no root login, no passwords, `MaxAuthTries 3`, `AllowUsers deploy`, idle timeout | Removes the two most attacked doors (root, passwords). Validated with `sshd -t` and reverted if invalid |
| Lockout guard | password auth stays **on** if the user has no key yet | Disabling passwords without a working key is the classic way to lose a server |
| ssh.socket | on Ubuntu 22.10+, a socket drop-in for a non-default port | Socket activation ignores `Port` in sshd_config, a common surprise |
| Firewall | ufw: deny incoming, allow outgoing, rate-limited SSH | Only SSH is reachable until something else is opened on purpose; `limit` slows brute force |
| fail2ban | `sshd` jail, 5 failures in 10 min → 1 h ban | Second layer behind key-only auth; keeps logs readable |
| Updates | daily unattended security upgrades | Most compromises use known, already-patched bugs |
| Kernel | `sysctl.d/90-hardening.conf`: reverse-path filter, no ICMP redirects or source routing, SYN cookies, restricted `dmesg` and kernel pointers, protected links | Standard CIS-style network hardening with no impact on normal workloads |
| journald | capped at 500 MB / 1 month | Stops logs filling the disk |
| Timezone | configurable, default UTC | Consistent timestamps across servers and logs |
| Swap | 1 GB swap file if none exists | Small VMs otherwise get OOM-killed under short spikes |
| Docker | official repository, log rotation (10 MB × 3), `live-restore`, `no-new-privileges` | Default Docker logs grow without limit; `live-restore` keeps containers up during daemon upgrades |

## Not done on purpose

- **Changing the SSH port by default.** It reduces log noise but is not a security control; it is available with `--ssh-port`.
- **Disabling IPv6.** Breaks more than it protects.
- **Installing a monitoring agent.** Depends on the stack; `healthcheck` plus the systemd timer in `examples/` covers the basics.
