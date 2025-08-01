import Foundation

class APIManager {
    static let shared = APIManager()
    private init() {}

    func send(messages: [[String: String]], apiKey: String) async throws -> String? {
        guard let url = URL(string: "https://openrouter.ai/api/v1/chat/completions") else { return nil }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")

        let payload: [String: Any] = ["model": "openrouter/cypher-alpha:free", "messages": messages, "stream": false]
        request.httpBody = try JSONSerialization.data(withJSONObject: payload)

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            let status = (response as? HTTPURLResponse)?.statusCode ?? -1
            throw NSError(domain: "API", code: status, userInfo: [NSLocalizedDescriptionKey: "Bad response: \(status)"])
        }
        if let obj = try JSONSerialization.jsonObject(with: data) as? [String: Any],
           let choices = obj["choices"] as? [[String: Any]],
           let msg = choices.first?["message"] as? [String: Any],
           let content = msg["content"] as? String {
            return content
        }
        return nil
    }
}
