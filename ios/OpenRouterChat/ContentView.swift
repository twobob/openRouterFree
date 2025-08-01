import SwiftUI

struct ChatMessage: Identifiable {
    let id = UUID()
    let role: String
    let content: String
}

struct ContentView: View {
    @State private var apiKey: String = KeychainHelper.shared.read(key: "OPENROUTER_KEY") ?? ""
    @State private var input: String = ""
    @State private var messages: [ChatMessage] = []
    @State private var isShowingKeyEntry = false
    @State private var isLoading = false

    var body: some View {
        NavigationView {
            VStack {
                ScrollViewReader { reader in
                    ScrollView {
                        LazyVStack(alignment: .leading) {
                            ForEach(messages) { msg in
                                HStack {
                                    Text(msg.role == "user" ? "You:" : "AI:")
                                        .bold()
                                    Text(msg.content)
                                    Spacer()
                                }
                                .padding(4)
                            }
                        }
                    }
                    .onChange(of: messages.count) { _ in
                        if let last = messages.last?.id {
                            withAnimation { reader.scrollTo(last, anchor: .bottom) }
                        }
                    }
                }

                HStack {
                    TextField("Message", text: $input)
                        .textFieldStyle(RoundedBorderTextFieldStyle())
                        .disabled(isLoading)
                    Button("Send") {
                        sendMessage()
                    }
                    .disabled(isLoading || input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
                .padding()
            }
            .navigationTitle("OpenRouter Chat")
            .toolbar {
                Button("API Key") { isShowingKeyEntry = true }
            }
            .sheet(isPresented: $isShowingKeyEntry) {
                NavigationView {
                    Form {
                        SecureField("API Key", text: $apiKey)
                    }
                    .navigationTitle("Set API Key")
                    .toolbar {
                        ToolbarItem(placement: .confirmationAction) {
                            Button("Save") {
                                KeychainHelper.shared.save(key: "OPENROUTER_KEY", value: apiKey)
                                isShowingKeyEntry = false
                            }
                        }
                        ToolbarItem(placement: .cancellationAction) {
                            Button("Cancel") { isShowingKeyEntry = false }
                        }
                    }
                }
            }
        }
    }

    func sendMessage() {
        let trimmed = input.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        guard !apiKey.isEmpty else {
            isShowingKeyEntry = true
            return
        }
        let userMsg = ChatMessage(role: "user", content: trimmed)
        messages.append(userMsg)
        input = ""
        isLoading = true

        Task {
            do {
                if let resp = try await APIManager.shared.send(messages: messages.map { ["role": $0.role, "content": $0.content] }, apiKey: apiKey) {
                    let aiMsg = ChatMessage(role: "assistant", content: resp)
                    messages.append(aiMsg)
                }
            } catch {
                messages.append(ChatMessage(role: "assistant", content: "Error: \(error.localizedDescription)"))
            }
            isLoading = false
        }
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
