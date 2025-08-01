# OpenRouterFree iOS

This folder contains a minimal SwiftUI application that allows using the OpenRouter API on iOS devices.

## Building

Open the `ios/OpenRouterChat` folder in Xcode and build for your desired iPhone target. The app stores the API key securely in the iOS Keychain.

## Usage

1. Launch the app.
2. Tap the **API Key** button to enter your OpenRouter API key. The key is stored in the Keychain and automatically loaded on subsequent launches.
3. Type a message and press **Send**. The response from the model appears in the chat history.

This is a simplified port of the original Tkinter application written in Python.
