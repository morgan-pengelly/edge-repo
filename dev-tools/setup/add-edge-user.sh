# Add edge user
echo "Adding edge user"
id -u edge &> /dev/null || adduser --disabled-password --gecos "" edge && sudo usermod -aG sudo edge
