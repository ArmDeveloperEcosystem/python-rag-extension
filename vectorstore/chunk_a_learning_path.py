from bs4 import BeautifulSoup
import argparse, requests, re, uuid, yaml, os, sys


# Global variables
github_raw_link = "https://raw.githubusercontent.com/ArmDeveloperEcosystem/arm-learning-paths/refs/heads/production/content"
site_link = "https://learn.arm.com"
chunk_index = 1

# Default Learning Path URL if not provided via argparse
default_lp = 'https://learn.arm.com/learning-paths/cross-platform/kleidiai-explainer'


class Chunk:
    def __init__(self, title, url, uuid, keywords, content):
        self.title = title
        self.url = url
        self.uuid = uuid
        self.content = content

        # Translate keyword list into comma-seperated string, and add similar words to keywords.
        self.keywords = self.formatKeywords(keywords)
    
    def formatKeywords(self,keywords):
        return ', '.join(keywords).lower().strip()

    # Used to dump into a yaml file easily
    def toDict(self):
        return {
            'title': self.title,
            'url': self.url,
            'uuid': self.uuid,
            'keywords': self.keywords,
            'content': self.content
        }

    def __repr__(self):
        return f"Chunk(title={self.title}, url={self.url}, uuid={self.uuid}, keywords={self.keywords}, content={self.content})"


def processLearningPath(url):
    def chunkizeLearningPath(relative_url, title, keywords):
        global chunk_index

        # 1) Construct proper URLs to obtain raw markdown content from GitHub
        if relative_url.endswith('/'):
            relative_url = relative_url[:-1]
        MARKDOWN_url = github_raw_link + relative_url + '.md'
        WEBSITE_url = site_link + relative_url

        # 2) Skip if url is invalid
        try:
            response = requests.get(WEBSITE_url)
            response.raise_for_status()  # Ensure we got a valid response
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred when accessing {WEBSITE_url}: {http_err}")

        # 3) Get markdown content from GitHub
        gh_response = requests.get(MARKDOWN_url)
        gh_response.raise_for_status()  # Ensure we got a valid response, throw exception if not
        md_content = gh_response.text
        markdown = md_content[md_content.find('---', 3)  + 3:].strip()  #  Remove frontmatter bounded by '---'    +3 to remove the '---' and strip to remove leading/trailing whitespace

        # 4) Get sized text snippets the markdown
        text_snippets = obtainTextSnippets__Markdown(markdown)

        # 5) Create chunk for each text_snippet & save to yaml file
        for text_snippet in text_snippets:
            chunk = Chunk(
                title        = title,
                url          = WEBSITE_url,
                uuid         = str(uuid.uuid4()),
                keywords     = keywords,
                content      = text_snippet
            )

            # Save chunk
            # Create ./chunks/ directory if it doesn't exist
            if not os.path.exists('./chunks/'):
                os.makedirs('./chunks/')
            with open(f"./chunks/chunk_{chunk_index}.yaml", 'w') as file:
                yaml.dump(chunk.toDict(), file, default_flow_style=False, sort_keys=False)
            print(f"   Chunk {chunk_index} saved, snippet of {len(text_snippet.split())}.")
            chunk_index += 1

    # Get Learning Path page elements
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all subpages in the Learning Path by iterating over its inner navigation and process them independently
    print('------------------------------------------------------------')
    for link in soup.find_all(class_='inner-learning-path-navbar-element'):
        
        if 'content-individual-a-mobile' not in link.get('class', []):                      # Ignore mobile links
            href = link.get('href')
            # Ignore files that have _index, _next-stpes, or _demo in their name
            if '0-weight' in link.get('class', []):                                         # Ignore index
                continue
            if any(substring in href for substring in ['_next-steps', '_demo']):            # Ignore next-steps and demo
                continue    

            title = 'Arm Learning Path - '+soup.find(id='learning-path-title').get_text()   # Obtain title of learning path

            ads_tags = soup.findAll('ads-tag')                                              # Obtain keywords of learning path, removing duplicates
            keywords = []
            for tag in ads_tags:
                keyword = tag.get_text().strip()
                if keyword not in keywords:
                    keywords.append(keyword)

            # Process each subpage
            chunkizeLearningPath(href,title,keywords)


    print('Completed chunking of', title)
    print('   from the url:', url)
    print('------------------------------------------------------------')


def obtainTextSnippets__Markdown(content, min_words=300, max_words=500, min_final_words=200):
    """Split content into chunks based on headers and word count constraints."""

    # Helper function to count words
    def word_count(text):
        return len(text.split())

    # Helper function to split content by a given heading level (e.g., h2, h3, h4)
    def split_by_heading(content, heading_level):
        pattern = re.compile(rf'(?<=\n)({heading_level} .+)', re.IGNORECASE)
        return pattern.split(content)

    # Helper function to chunk content based on custom rules for Learning Path-formatted content
    def create_chunks(content_pieces, heading_level='##'):
        chunks = []
        current_chunk = ""
        current_word_count = 0

        for piece in content_pieces:
            piece_word_count = word_count(piece)

            # Check if the current piece starts with the heading level, indicating the start of a new section
            if re.match(rf'^{heading_level} ', piece.strip()):
                # If the current chunk has enough words, finalize it and start a new chunk
                if current_word_count >= min_words:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                    current_word_count = 0

            # Add the piece to the current chunk
            if current_word_count + piece_word_count > max_words and current_word_count >= min_words:
                # If adding this piece exceeds max_words, finalize the current chunk
                chunks.append(current_chunk.strip())
                current_chunk = piece.strip()
                current_word_count = piece_word_count
            else:
                current_chunk += piece + "\n"
                current_word_count += piece_word_count

        # Handle the last chunk
        if current_chunk.strip():
            if current_word_count < min_final_words and chunks:
                # If the last chunk is too small, merge it with the previous chunk
                chunks[-1] += "\n" + current_chunk.strip()
            else:
                # Otherwise, add it as a separate chunk
                chunks.append(current_chunk.strip())

        return chunks

    # 1. Split by h2 headings
    content_pieces = split_by_heading(content, '##')
    chunks = create_chunks(content_pieces)

    # 2. Further split large chunks by h3 if they exceed max_words
    final_chunks = []
    for chunk in chunks:
        if word_count(chunk) > max_words:
            sub_pieces = split_by_heading(chunk, '###')
            sub_chunks = create_chunks(sub_pieces,'###')
            
            # 3. Further split large sub-chunks by h4 if they exceed max_words
            for sub_chunk in sub_chunks:
                if word_count(sub_chunk) > max_words:
                    sub_sub_pieces = split_by_heading(sub_chunk, '####')
                    sub_sub_chunks = create_chunks(sub_sub_pieces,'####')
                    
                    # 4. If still too large, split by paragraph
                    for sub_sub_chunk in sub_sub_chunks:
                        if word_count(sub_sub_chunk) > max_words:
                            paragraphs = sub_sub_chunk.split('\n\n')
                            paragraph_chunks = create_chunks(paragraphs)
                            final_chunks.extend(paragraph_chunks)
                        else:
                            final_chunks.append(sub_sub_chunk)
                else:
                    final_chunks.append(sub_chunk)
        else:
            final_chunks.append(chunk)

    return final_chunks


def main():
    # Argparse input for a single learning path URL. If none given, default to a known-good Learning Path URL.
    parser = argparse.ArgumentParser(description="Turn a Learning Path (specified via URL) into a chunk ready for RAG.")
    parser.add_argument("--url", nargs='?', default=default_lp, help=f"Full path to a Learning Path to chunk. If none specified, defaults to {default_lp}")
    args = parser.parse_args()
    lp_url = args.url

    processLearningPath(lp_url)

if __name__ == "__main__":
    main()