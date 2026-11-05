# WhatsApp: who pays, and what actually gets delivered

Learned running the bot in production (WhatsApp Cloud API):

- **Free or paid depends on who wrote first, not on the template category.** If you write first, every template is paid (utility included). If the candidate wrote first, your replies are free for 24 h. If they wrote first from a click-to-WhatsApp ad, replies are free for 72 h.
- **A Meta lead form does NOT open a free window.** Leads from a form need a paid template, or email.
- **Default funnel = click-to-WhatsApp ad**, not a lead form: the candidate says hi first, so the whole screening conversation is free. Ramón turns any unknown number whose message comes from an ad (`referral`) or mentions applying (apply/job/sdr/bdr/trabajo/vacante...) into a candidate.
- **"accepted" is not "delivered".** If the WhatsApp Business account has no payment method, Meta accepts template sends and then drops them at delivery (error 131042). Check delivery status webhooks before you report anything as sent.
- **Form leads with no window:** email the test link plus a `wa.me/<your number>` "say hi" link. Once they say hi, the bot replies for free.
- **Username-only users** (no phone number in the payload) can't be merged by phone. The bot posts them to the team channel to answer by hand.
- Keep templates short, one link, no URL shorteners.
