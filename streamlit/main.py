import streamlit as st
import requests

# Set the page configuration
st.set_page_config(
    page_title="Kloudstax: To&From",
    layout="wide" 
)

# Streamlit app title
st.title("Kloudstax: To&From")

# User input for query
user_query = st.text_area("Enter your query:", height=100)

# User input for Bearer Token
bearer_token = st.text_input("Enter your Bearer Token:", type="password")

# Dropdown to select the Cloud Function URL
url_options = {
    "Gemini - Split Approach": "https://us-central1-kloudstax-429211.cloudfunctions.net/gemini-gemini",
    "Gemini - Basic Approach": "https://us-central1-kloudstax-429211.cloudfunctions.net/to-and-from"
}
selected_url_name = st.selectbox("Select Cloud Function", list(url_options.keys()))
gcf_url = url_options[selected_url_name]

# Function to fetch product details, including images
def fetch_product_details(product_id):
    try:
        response = requests.get(f"https://api.toandfrom.com/v2/product/{product_id}")
        response.raise_for_status()
        data = response.json()

        # Extract the image URL
        if data.get("image") and len(data["image"]) > 0:
            return decodeURIComponent(data["image"][0]["link"])
        else:
            return "https://via.placeholder.com/100"
    except requests.RequestException as e:
        st.error(f"Error fetching product details for {product_id}: {e}")
        return "https://via.placeholder.com/100"

# Function to decode URI component
def decodeURIComponent(url):
    from urllib.parse import unquote
    return unquote(url)

# Button to send the request
if st.button("Send Request"):
    if user_query and bearer_token:
        # Set up headers with Bearer Token
        headers = {
            "Authorization": f"Bearer {bearer_token}"
        }

        # Send the request with the headers
        response = requests.get(f"{gcf_url}?query={user_query}", headers=headers)

        if response.status_code == 200:
            # Parse the JSON response
            data = response.json()

            # Display Attributes
            st.header("Attributes")
            st.write(", ".join(data.get("attributes", [])))

            # Display Products with Images
            st.header("Products")
            products_info = data.get("products", [])
            cols = st.columns(4)  # Number of columns for layout
            for idx, product in enumerate(products_info):
                col = cols[idx % 4]
                with col:
                    product_id = product.get("id", "")
                    image_url = fetch_product_details(product_id)
                    st.image(image_url, width=200, caption=f"Rank: {product.get('rank', 'No rank')}")
                    st.write(f"Product ID: {product_id}")
                    product_url = product.get('url', 'No URL')
                    if product_url != 'No URL':
                        st.write(f"Product URL: [View Product]({product_url})")
                    else:
                        st.write("Product URL: No URL")
                    st.write("---")

            # Display Debug Information with Images
            st.header("Debug Information")
            debug_info = data.get("debug", [])
            cols = st.columns(4)

            for idx, debug_item in enumerate(debug_info):
                col = cols[idx % 4]
                with col:
                    image_url = fetch_product_details(debug_item.get("id", ""))
                    st.image(image_url, width=200, caption=debug_item.get("name", "No name provided"))
                    st.write(f"Brand: {debug_item.get('brandName', 'No brand name')}")
                    st.write(f"Description: {debug_item.get('description', 'No description')}")
                    st.write(f"Price: {debug_item.get('price', 'No price')/100}")
                    st.write(f"Attributes: {', '.join(debug_item.get('attributes', []))}")
                    product_url = debug_item.get('url', 'No URL')
                    if product_url != 'No URL':
                        st.write(f"Product URL: [View Product]({product_url})")
                    else:
                        st.write("Product URL: No URL")
                    st.write("---")
        else:
            st.error(f"Failed to retrieve data. Status code: {response.status_code}")
    else:
        st.error("Please enter both a query and a Bearer Token.")
