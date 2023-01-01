<div align="left">
    <h1>Modmail Premium Logviewer</h1>
    <strong><i>The premium version of Logviewer that includes OAuth2 support.</i></strong>
    <br>
    <br>


<a href="https://heroku.com/deploy?template=https://github.com/kyb3rr/logviewer-premium">
    <img src="https://img.shields.io/badge/deploy_to-heroku-997FBC.svg?style=for-the-badge" />
</a>

</div>

## What is this?

In order for you to view your self-hosted logs, you have to deploy this application. Before you deploy the application, create an environment variable named `MONGO_URI` and set it as your MongoDB connection URI. Once you deployed this Logviewer, set the URL under the `LOG_URL` environment variable for the Modmail bot application.

For Heroku hosting: before you press the deploy button, make sure your GitHub account is connected to your Heroku account.


## Discord OAuth2 setup

To enable Discord OAuth2 support (login via Discord to view logs), you will need to set up a few more environment variables.

- `GUILD_ID` - the Guild ID of your modmail inbox server, this is required so the server can check if a user has a whitelisted role.
- `TOKEN` - Token of your modmail bot, required for the same reason as above.
- `OAUTH2_CLIENT_ID` - The ID of your bot.
- `OAUTH2_CLIENT_SECRET` - Get this from the general information section of your bot app in the Discord dev portal.
<img src='https://i.imgur.com/YBavWlV.png' height=100>

- `OAUTH2_REDIRECT_URI` - This will be equal to the URL of your log viewer app + `/callback` e.g. `https://logwebsite.com/callback`. You will need to add this same URL as a redirect URL in the OAuth2 section in the Discord dev portal. 
<img src='https://i.imgur.com/evZIWYN.png' height=100>

Now you need to set up users or roles to whitelist access to your logs, do this via the `?oauth whitelist @user/role` command on your Modmail bot. 

This should allow whitelisted users to view logs, while rejecting anyone else trying to access them.

## Updating

Simply re-deploy the updated Logviewer using the same configs.

## Contributing

If you can make improvements in the design and presentation of logs, please make a pull request with changes.
