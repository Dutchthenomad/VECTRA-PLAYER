// Synthesize automated review feedback
// Usage: node .github/scripts/synthesize-reviews.js <PR_NUMBER>

const { Octokit } = require("@octokit/rest");

const octokit = new Octokit({ auth: process.env.GITHUB_TOKEN });
const [owner, repo] = process.env.GITHUB_REPOSITORY.split("/");
const prNumber = process.argv[2];

async function synthesizeReviews() {
  // Fetch all comments and reviews
  const { data: comments } = await octokit.issues.listComments({
    owner,
    repo,
    issue_number: prNumber,
  });

  const { data: reviews } = await octokit.pulls.listReviews({
    owner,
    repo,
    pull_number: prNumber,
  });

  // Filter bot comments
  const botNames = ["sourcery-ai", "coderabbitai", "copilot", "qodo"];
  const botComments = comments.filter((c) =>
    botNames.some((bot) => c.user.login.toLowerCase().includes(bot))
  );

  // Categorize feedback
  const categorized = {
    critical: [],
    high: [],
    optional: [],
    duplicate: [],
  };

  // Simple keyword-based categorization
  botComments.forEach((comment) => {
    const body = comment.body.toLowerCase();
    if (
      body.includes("security") ||
      body.includes("critical") ||
      body.includes("bug")
    ) {
      categorized.critical.push({ bot: comment.user.login, text: comment.body });
    } else if (
      body.includes("performance") ||
      body.includes("should")
    ) {
      categorized.high.push({ bot: comment.user.login, text: comment.body });
    } else {
      categorized.optional.push({ bot: comment.user.login, text: comment.body });
    }
  });

  // Generate synthesis comment
  const synthesis = `
## 🤖 Automated Review Synthesis

### Summary
Found ${botComments.length} comments from ${new Set(botComments.map(c => c.user.login)).size} review bots.

### 🔴 Critical Issues (${categorized.critical.length})
${categorized.critical.map((item, i) => `${i + 1}. **${item.bot}**: ${item.text.slice(0, 200)}...`).join("\n")}

### 🟡 High Priority (${categorized.high.length})
${categorized.high.map((item, i) => `${i + 1}. **${item.bot}**: ${item.text.slice(0, 200)}...`).join("\n")}

### 🟢 Optional Improvements (${categorized.optional.length})
See individual bot comments for details.

### Recommendations
- **Address in this PR:** All critical issues
- **Consider for this PR:** High priority items
- **Defer to follow-up:** Optional improvements

### Suggested Follow-up Issues
Would you like me to create issues for the deferred items? Reply with \`yes\` to auto-create.
`;

  // Post synthesis comment
  await octokit.issues.createComment({
    owner,
    repo,
    issue_number: prNumber,
    body: synthesis,
  });

  console.log("Synthesis posted!");
}

synthesizeReviews().catch(console.error);
