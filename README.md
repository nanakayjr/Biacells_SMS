# Baicells SMS

**Baicells SMS** is a Home Assistant custom integration for reading text messages stored on the SIM card in a Baicells router. Messages are shown in Home Assistant, saved locally, and can be deleted from the SIM after a successful read.

> [!WARNING]
> The default setting deletes messages from the SIM after they are read. Turn off **Delete SMS from SIM after read** during setup if you want to keep messages on the SIM card.

## What it does

- Connects directly to your Baicells router over SSH.
- Reads SIM messages at a frequency you choose.
- Shows sender, date/time, and message text in Home Assistant.
- Provides a **Baicells SMS Force Read** button for an immediate update.
- Saves a permanent text and JSON archive in Home Assistant.
- Supports the older SSH algorithms commonly required by Baicells routers.

## Before you begin

Have the following information ready:

| Setting | Example | Default |
| --- | --- | --- |
| Router IP address | `192.168.150.1` | — |
| SSH port | `27149` | `27149` |
| SSH user | `root` | `root` |
| SSH password | Your router password | — |
| Modem device | `/dev/ttyUSB1` | `/dev/ttyUSB1` |

The Home Assistant host must be able to reach the router’s SSH port. Confirm that SSH is enabled on the router before adding the integration.

## Install with HACS

1. In Home Assistant, open **HACS**.
2. Select **Integrations**.
3. Select the three-dot menu, then **Custom repositories**.
4. Add `https://github.com/twumduan/Biacells_SMS` with category **Integration**.
5. Find **Baicells SMS** in HACS and select **Download**.
6. Restart Home Assistant.
7. Go to **Settings → Devices & services → Add integration**.
8. Search for **Baicells SMS**, then enter your router settings.

## Manual installation

1. Copy the [custom_components/baicells_sms](custom_components/baicells_sms) folder to the `custom_components` folder in your Home Assistant configuration directory.
2. Restart Home Assistant.
3. Add **Baicells SMS** through **Settings → Devices & services → Add integration**.

## Setup options

The initial setup and the integration’s **Configure** option provide these settings:

| Option | Meaning |
| --- | --- |
| **Router IP** | The local IP address or hostname of your Baicells router. |
| **SSH Port** | The router SSH port; Baicells commonly uses `27149`. |
| **SSH Username / Password** | Router login credentials. The password is stored in Home Assistant’s encrypted configuration storage where supported. |
| **Modem Device Path** | Serial device used by the router modem; normally `/dev/ttyUSB1`. |
| **Read Frequency** | How often to check the SIM, in seconds. Minimum: 30 seconds. Default: 300 seconds (5 minutes). |
| **SSH Command Timeout** | Maximum time allowed for one modem read. Default: 30 seconds. |
| **Delete SMS from SIM after read** | Deletes all SIM messages after the read completes. Enabled by default. |
| **Enforce host key verification** | Checks the router host key against Home Assistant’s `known_hosts` file. Leave disabled unless you have configured that file. |
| **Logo path** | Optional Home Assistant web path used as the inbox entity picture. |

Changing an option reloads the integration automatically.

## Entities

After setup, Home Assistant creates:

- **Baicells SMS Inbox** sensor — its state is the number of messages held in the local archive.
- **Baicells SMS Force Read** button — reads the SIM immediately.

The inbox sensor includes a `messages` attribute. Each message contains `sender`, `timestamp`, and `text`, ready for dashboards and automations.

## Add the inbox to a dashboard

Add a **Markdown** card, switch to the YAML editor, and replace `sensor.baicells_sms_inbox` with the entity id shown in **Developer tools → States**:

```yaml
type: markdown
title: Baicells SMS Inbox
content: >
  {% set messages = state_attr('sensor.baicells_sms_inbox', 'messages') or [] %}
  {% if not messages %}
  No saved SMS messages.
  {% else %}
  {% for message in messages %}
  ## {{ message.sender }}
  _{{ message.timestamp }}_

  {{ message.text }}

  ---
  {% endfor %}
  {% endif %}
```

To add an on-demand refresh button:

```yaml
type: button
name: Read SIM messages now
icon: mdi:refresh
tap_action:
  action: call-service
  service: baicells_sms.force_read
```

The same action is available to automations as the `baicells_sms.force_read` service. When more than one router is configured, provide the optional `entry_id` service field to refresh only one router.

## Logo

This repository includes a logo at [custom_components/baicells_sms/logo.png](custom_components/baicells_sms/logo.png). To display it in Home Assistant:

1. Create `/config/www/baicells_sms/` on your Home Assistant host.
2. Copy the bundled `logo.png` to `/config/www/baicells_sms/logo.png`.
3. Leave the integration’s **Logo path** at `/local/baicells_sms/logo.png`.

To use another image, place it under `/config/www/` and set **Logo path** to the corresponding `/local/...` URL. For example, `/config/www/my_logo.png` becomes `/local/my_logo.png`.

## Message files

Messages are stored on the Home Assistant host under `/config/baicells_sms/`:

- `<entry_id>_messages.txt` — readable append-only archive.
- `<entry_id>_messages.json` — persistent history used by the integration.

Back up this folder if messages are important. Do not edit the JSON file while Home Assistant is running.

## Security and compatibility

Some Baicells firmware requires obsolete SSH cryptography. This integration enables the router’s required legacy key exchange, host-key, and cipher algorithms only for its connection.

- Use it only on a trusted local network.
- Do not expose router SSH to the internet.
- Use a strong router password.
- Enable host-key verification after you have created and maintained a suitable `/config/known_hosts` file.

## Troubleshooting

| Problem | Check |
| --- | --- |
| Integration cannot connect | Verify router IP, port, credentials, Home Assistant network reachability, and SSH service. |
| No messages are found | Confirm the SIM is active and verify the modem device path. `/dev/ttyUSB1` is only the default. |
| Messages remain on SIM | Enable **Delete SMS from SIM after read** and force a read. |
| Logo does not appear | Verify the file is under `/config/www/` and that the configured URL starts with `/local/`. Clear browser cache after replacing it. |

## Version

Current version: **1.0.0**.

## License

Released under the [MIT License](LICENSE).
